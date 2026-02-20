#include "apiclient.h"
#include <QtConcurrent>
#include <QNetworkRequest>
#include <QHttpMultiPart>
#include <QUrl>

ApiClient::ApiClient(QObject *parent, const QString& baseUrl)
    : QObject(parent), m_baseUrl(baseUrl) {
    m_manager = new QNetworkAccessManager(this);
}

QFuture<QJsonDocument> ApiClient::post(const QString& endpoint, const QJsonObject& data) {
    QPromise<QJsonDocument> promise;
    QFuture<QJsonDocument> future = promise.future();
    
    QNetworkRequest request(QUrl(m_baseUrl + endpoint));
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    
    QByteArray body = QJsonDocument(data).toJson();
    QNetworkReply* reply = m_manager->post(request, body);
    
    connect(reply, &QNetworkReply::finished, this, [reply, promise]() mutable {
        if (reply->error() == QNetworkReply::NoError) {
            promise.addResult(QJsonDocument::fromJson(reply->readAll()));
        } else {
            promise.setException(std::make_exception_ptr(
                std::runtime_error(reply->errorString().toStdString())
            ));
        }
        reply->deleteLater();
        promise.finish();
    });
    
    promise.start();
    return future;
}

QFuture<QJsonDocument> ApiClient::get(const QString& endpoint) {
    QPromise<QJsonDocument> promise;
    QFuture<QJsonDocument> future = promise.future();
    
    QNetworkRequest request(QUrl(m_baseUrl + endpoint));
    QNetworkReply* reply = m_manager->get(request);
    
    connect(reply, &QNetworkReply::finished, this, [reply, promise]() mutable {
        if (reply->error() == QNetworkReply::NoError) {
            promise.addResult(QJsonDocument::fromJson(reply->readAll()));
        } else {
            promise.setException(std::make_exception_ptr(
                std::runtime_error(reply->errorString().toStdString())
            ));
        }
        reply->deleteLater();
        promise.finish();
    });
    
    promise.start();
    return future;
}

QFuture<QUuid> ApiClient::createRun(const QString& sourceType, const QString& scopeJson) {
    QJsonObject data;
    data["source_type"] = sourceType;
    data["scope_json"] = scopeJson;
    
    return post("/runs/create", data).then([](const QJsonDocument& doc) {
        return QUuid(doc.object()["run_id"].toString());
    });
}

QFuture<void> ApiClient::startIndexing(const QUuid& runId) {
    return post(QString("/runs/start_indexing/%1").arg(runId.toString()), QJsonObject())
        .then([](const QJsonDocument&) {});
}

QFuture<void> ApiClient::discoveringStopped(const QUuid& runId) {
    return post(QString("/runs/discovering_stopped/%1").arg(runId.toString()), QJsonObject())
        .then([](const QJsonDocument&) {});
}

QFuture<void> ApiClient::requestStop(const QUuid& runId) {
    return post(QString("/runs/request_stop/%1").arg(runId.toString()), QJsonObject())
        .then([](const QJsonDocument&) {});
}

QFuture<void> ApiClient::markFailed(const QUuid& runId, const QString& errorMessage) {
    QJsonObject data;
    data["error_message"] = errorMessage;
    return post(QString("/runs/mark_failed/%1").arg(runId.toString()), data)
        .then([](const QJsonDocument&) {});
}

QFuture<bool> ApiClient::isStopRequested(const QUuid& runId) {
    return get(QString("/runs/is_stop_requested/%1").arg(runId.toString()))
        .then([](const QJsonDocument& doc) {
            return doc.object()["stop_requested"].toBool();
        });
}

QFuture<void> ApiClient::queueDocumentPart(const QUuid& runId, const DocumentPart& part, const QString& scopeJson) {
    QJsonObject data;
    data["part"] = part.toJson();
    data["run_id"] = runId.toString();
    data["part"]["scope_json"] = scopeJson;
    
    return post("/queue/add", data).then([](const QJsonDocument&) {});
}

QFuture<QList<SearchResult>> ApiClient::search(const QString& query, int topK) {
    QJsonObject data;
    data["query"] = query;
    data["top_k"] = topK;
    
    return post("/search", data).then([](const QJsonDocument& doc) -> QList<SearchResult> {
        QList<SearchResult> results;
        QJsonArray hits = doc.object()["results"].toArray();
        
        for (const auto& hit : hits) {
            SearchResult result;
            QJsonObject obj = hit.toObject();
            result.score = obj["score"].toDouble();
            // Document details fetched separately via batchGet
            result.document.documentPartId = QUuid(obj["document_part_id"].toString());
            results.append(result);
        }
        return results;
    });
}

QFuture<QList<DocumentPart>> ApiClient::batchGetDocuments(const QList<QUuid>& ids) {
    QJsonObject data;
    QJsonArray arr;
    for (const auto& id : ids) arr.append(id.toString());
    data["document_part_ids"] = arr;
    
    return post("/documents/batch_get", data).then([](const QJsonDocument& doc) -> QList<DocumentPart> {
        QList<DocumentPart> parts;
        QJsonArray docs = doc.object()["documents_parts"].toArray();
        for (const auto& d : docs) {
            parts.append(DocumentPart::fromJson(d.toObject()));
        }
        return parts;
    });
}

QFuture<QJsonObject> ApiClient::getOpenDescriptor(const QUuid& documentPartId) {
    return get(QString("/documents/open/%1").arg(documentPartId.toString()))
        .then([](const QJsonDocument& doc) { return doc.object(); });
}

QFuture<QUuid> ApiClient::addSource(const QString& sourceType, const QString& scopeJson) {
    QJsonObject data;
    data["source_type"] = sourceType;
    data["scope"] = QJsonDocument::fromJson(scopeJson.toUtf8()).object();
    
    return post("/sources/add", data).then([](const QJsonDocument& doc) {
        return QUuid(doc.object()["source_id"].toString());
    });
}

QFuture<QJsonArray> ApiClient::getAllSources() {
    return get("/sources/get_all_sources").then([](const QJsonDocument& doc) {
        return doc.object()["sources"].toArray();
    });
}

QFuture<QList<IndexingRun>> ApiClient::listRuns() {
    return get("/runs/list").then([](const QJsonDocument& doc) -> QList<IndexingRun> {
        QList<IndexingRun> runs;
        QJsonArray arr = doc.object()["runs"].toArray();
        for (const auto& r : arr) {
            runs.append(IndexingRun::fromJson(r.toObject()));
        }
        return runs;
    });
}

QFuture<IndexingRun> ApiClient::stopLatest(const QString& sourceType) {
    return post(QString("/runs/stop_latest/%1").arg(sourceType), QJsonObject())
        .then([](const QJsonDocument& doc) { return IndexingRun::fromJson(doc.object()); });
}

QFuture<IndexingRun> ApiClient::resumeLatest(const QString& sourceType) {
    return get(QString("/runs/resume_latest/%1").arg(sourceType))
        .then([](const QJsonDocument& doc) { return IndexingRun::fromJson(doc.object()); });
}
