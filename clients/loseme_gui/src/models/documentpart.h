#ifndef DOCUMENTPART_H
#define DOCUMENTPART_H

#include <QString>
#include <QDateTime>
#include <QJsonObject>
#include <QUuid>

struct DocumentPart {
    QUuid documentPartId;
    QString sourceType;
    QString checksum;
    QString deviceId;
    QString sourcePath;
    QString sourceInstanceId;
    QString unitLocator;
    QString contentType;
    QString extractorName;
    QString extractorVersion;
    QJsonObject metadataJson;
    QDateTime createdAt;
    QDateTime updatedAt;
    QString text;
    QString scopeJson;
    
    static DocumentPart fromJson(const QJsonObject& obj) {
        DocumentPart part;
        part.documentPartId = QUuid(obj["document_part_id"].toString());
        part.sourceType = obj["source_type"].toString();
        part.checksum = obj["checksum"].toString();
        part.deviceId = obj["device_id"].toString();
        part.sourcePath = obj["source_path"].toString();
        part.sourceInstanceId = obj["source_instance_id"].toString();
        part.unitLocator = obj["unit_locator"].toString();
        part.contentType = obj["content_type"].toString();
        part.extractorName = obj["extractor_name"].toString();
        part.extractorVersion = obj["extractor_version"].toString();
        part.metadataJson = obj["metadata_json"].toObject();
        part.createdAt = QDateTime::fromString(obj["created_at"].toString(), Qt::ISODate);
        part.updatedAt = QDateTime::fromString(obj["updated_at"].toString(), Qt::ISODate);
        part.text = obj["text"].toString();
        part.scopeJson = obj["scope_json"].toString();
        return part;
    }
    
    QJsonObject toJson() const {
        QJsonObject obj;
        obj["document_part_id"] = documentPartId.toString();
        obj["source_type"] = sourceType;
        obj["checksum"] = checksum;
        obj["device_id"] = deviceId;
        obj["source_path"] = sourcePath;
        obj["source_instance_id"] = sourceInstanceId;
        obj["unit_locator"] = unitLocator;
        obj["content_type"] = contentType;
        obj["extractor_name"] = extractorName;
        obj["extractor_version"] = extractorVersion;
        obj["metadata_json"] = metadataJson;
        obj["created_at"] = createdAt.toString(Qt::ISODate);
        obj["updated_at"] = updatedAt.toString(Qt::ISODate);
        obj["text"] = text;
        obj["scope_json"] = scopeJson;
        return obj;
    }
};

struct SearchResult {
    DocumentPart document;
    double score = 0.0;
};

#endif // DOCUMENTPART_H
