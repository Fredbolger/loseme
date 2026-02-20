#ifndef APICLIENT_H
#define APICLIENT_H

#include <QObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QFuture>
#include <QPromise>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include "models/documentpart.h"
#include "models/indexingscope.h"
#include "models/runstatus.h"

class ApiClient : public QObject {
    Q_OBJECT

public:
    explicit ApiClient(QObject *parent = nullptr, const QString& baseUrl = "http://localhost:8000");
    
    // Async methods returning QFuture for composition
    QFuture<QUuid> createRun(const QString& sourceType, const QString& scopeJson);
    QFuture<void> startIndexing(const QUuid& runId);
    QFuture<void> discoveringStopped(const QUuid& runId);
    QFuture<void> requestStop(const QUuid& runId);
    QFuture<void> markFailed(const QUuid& runId, const QString& errorMessage);
    QFuture<bool> isStopRequested(const QUuid& runId);
    QFuture<void> queueDocumentPart(const QUuid& runId, const DocumentPart& part, const QString& scopeJson);
    
    // Search
    QFuture<QList<SearchResult>> search(const QString& query, int topK);
    QFuture<QList<DocumentPart>> batchGetDocuments(const QList<QUuid>& ids);
    QFuture<QJsonObject> getOpenDescriptor(const QUuid& documentPartId);
    
    // Sources
    QFuture<QUuid> addSource(const QString& sourceType, const QString& scopeJson);
    QFuture<QJsonArray> getAllSources();
    
    // Runs management
    QFuture<QList<IndexingRun>> listRuns();
    QFuture<IndexingRun> stopLatest(const QString& sourceType);
    QFuture<IndexingRun> resumeLatest(const QString& sourceType);

private:
    QNetworkAccessManager* m_manager;
    QString m_baseUrl;
    
    QFuture<QJsonDocument> post(const QString& endpoint, const QJsonObject& data);
    QFuture<QJsonDocument> get(const QString& endpoint);
    // FIX: removed declaration of handleReply() — it was declared but never implemented,
    //      which would cause a linker error.
};

#endif // APICLIENT_H
