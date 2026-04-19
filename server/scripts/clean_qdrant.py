#!/usr/bin/env python3
"""
Create optimized collection with binary quantization and reduced Colbert dimension
Copies only active points from chunks to chunks1
"""

import requests
import json
from typing import List, Dict, Any
import time

# Qdrant configuration
QDRANT_HOST = "http://localhost:6333"
SOURCE_COLLECTION = "chunks"
TARGET_COLLECTION = "chunks1"
BATCH_SIZE = 5  # Small batches due to large points

def get_source_config():
    """Get source collection configuration"""
    response = requests.get(f"{QDRANT_HOST}/collections/{SOURCE_COLLECTION}")
    response.raise_for_status()
    return response.json()["result"]["config"]["params"]

def create_optimized_collection():
    """Create new collection with optimized settings"""
    print("📦 Creating optimized collection 'chunks1'...")
    
    # Optimized configuration
    create_config = {
        "vectors": {
            "dense": {
                "size": 1024,
                "distance": "Cosine",
                "on_disk": False  # Keep dense in RAM for speed
            },
            "colbert": {
                "size": 128,  # 👈 Reduced from 1024 (8x reduction)
                "distance": "Cosine",
                "multivector_config": {
                    "comparator": "max_sim"
                },
                "on_disk": True  # 👈 Colbert on disk to save RAM
            }
        },
        "sparse_vectors": {
            "sparse": {
                "index": {
                    "on_disk": True
                }
            }
        },
        "on_disk_payload": True,
        "quantization_config": {
            "binary": {  # 👈 Binary quantization for all vectors
                "always_ram": False  # Don't keep binary vectors in RAM
            }
        },
        "optimizers_config": {
            "deleted_threshold": 0.2,
            "vacuum_min_vector_number": 1000
        }
    }
    
    # Delete if exists
    try:
        requests.delete(f"{QDRANT_HOST}/collections/{TARGET_COLLECTION}")
        print("  Deleted existing chunks1 collection")
        time.sleep(1)
    except:
        pass
    
    # Create new collection
    response = requests.put(
        f"{QDRANT_HOST}/collections/{TARGET_COLLECTION}",
        json=create_config,
        timeout=60
    )
    response.raise_for_status()
    print("✅ Optimized collection created")
    print(f"   - Dense: 1024-dim (RAM)")
    print(f"   - Colbert: 128-dim, on-disk (8x reduction)")
    print(f"   - Binary quantization enabled")

def scroll_points(limit: int = 10, offset: str = None) -> Dict:
    """Scroll through points in source collection"""
    payload = {
        "limit": limit,
        "with_payload": True,
        "with_vector": True
    }
    if offset:
        payload["offset"] = offset
    
    response = requests.post(
        f"{QDRANT_HOST}/collections/{SOURCE_COLLECTION}/points/scroll",
        json=payload,
        timeout=60
    )
    response.raise_for_status()
    return response.json()["result"]

def transform_vectors(point: Dict) -> Dict:
    """Transform vectors to match new collection schema"""
    original_vectors = point.get("vector", {})
    
    # Transform colbert vector: reduce dimension from 1024 to 128
    # This averages/samples every 8th dimension
    transformed_vectors = {}
    
    # Copy dense as-is
    if "dense" in original_vectors:
        transformed_vectors["dense"] = original_vectors["dense"]
    
    # Reduce colbert dimension
    if "colbert" in original_vectors:
        colbert_original = original_vectors["colbert"]
        
        # Colbert is a list of token vectors: each is [1024] -> reduce to [128]
        if isinstance(colbert_original, list) and len(colbert_original) > 0:
            reduced_colbert = []
            for token_vector in colbert_original:
                # Simple dimension reduction: take every 8th element
                # (1024 / 8 = 128)
                reduced_token = token_vector[::8]  # Sample every 8th dimension
                reduced_colbert.append(reduced_token)
            transformed_vectors["colbert"] = reduced_colbert
        else:
            transformed_vectors["colbert"] = colbert_original
    
    # Copy sparse as-is
    if "sparse" in original_vectors:
        transformed_vectors["sparse"] = original_vectors["sparse"]
    
    return transformed_vectors

def upsert_points(points: List[Dict]):
    """Insert transformed points into target collection"""
    formatted_points = []
    
    for point in points:
        # Transform vectors to new dimensions
        transformed_vectors = transform_vectors(point)
        
        formatted_point = {
            "id": point["id"],
            "vector": transformed_vectors,
            "payload": point.get("payload", {})
        }
        formatted_points.append(formatted_point)
    
    # Upsert in small batches
    for i in range(0, len(formatted_points), BATCH_SIZE):
        batch = formatted_points[i:i+BATCH_SIZE]
        
        response = requests.put(
            f"{QDRANT_HOST}/collections/{TARGET_COLLECTION}/points",
            json={"points": batch},
            timeout=120
        )
        
        if response.status_code != 200:
            print(f"    ❌ Error: {response.text[:200]}")
            response.raise_for_status()
        
        print(f"    ✓ Upserted {len(batch)} points")

def copy_collection():
    """Main copy function"""
    print("=" * 60)
    print("Creating Optimized Collection: chunks1")
    print("=" * 60)
    
    # Step 1: Create optimized collection
    create_optimized_collection()
    
    # Step 2: Scroll and copy points
    print("\n📖 Copying points from source collection...")
    total_points = 0
    next_offset = None
    
    while True:
        result = scroll_points(limit=10, offset=next_offset)
        points = result.get("points", [])
        
        if not points:
            break
        
        total_points += len(points)
        print(f"\n  Read {len(points)} points (total: {total_points})")
        print(f"  🔄 Transforming vectors (1024-dim → 128-dim Colbert)...")
        upsert_points(points)
        
        # Check if there are more points
        next_offset = result.get("next_page_offset")
        if not next_offset:
            break
    
    print(f"\n✅ Copy complete! Copied {total_points} points to 'chunks1'")
    
    # Step 3: Verify
    print("\n🔍 Verifying...")
    source_info = requests.get(f"{QDRANT_HOST}/collections/{SOURCE_COLLECTION}").json()
    target_info = requests.get(f"{QDRANT_HOST}/collections/{TARGET_COLLECTION}").json()
    
    source_count = source_info["result"]["points_count"]
    target_count = target_info["result"]["points_count"]
    
    print(f"  Source points: {source_count}")
    print(f"  Target points: {target_count}")
    
    if source_count == target_count:
        print("  ✅ Counts match!")
    else:
        print(f"  ⚠️ Warning: Counts don't match!")
    
    # Step 4: Show storage savings
    print("\n💾 Check storage size:")
    print("  Run: docker exec loseme-qdrant-1 du -sh /qdrant/storage/collections/chunks1/")
    print("\n🎯 Expected size: 1-2 GB (from 92 GB)")

if __name__ == "__main__":
    try:
        copy_collection()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
