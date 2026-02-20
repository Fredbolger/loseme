#ifndef RUNSTATUS_H
#define RUNSTATUS_H

#include <QString>
#include <QUuid>
#include <QDateTime>
#include <QJsonObject>

enum class RunStatus {
    Created,
    Indexing,
    Discovering,
    Completed,
    Failed,
    Stopped
};

struct IndexingRun {
    QUuid runId;
    QString sourceType;
    QString status;
    QString scopeJson;
    QDateTime createdAt;
    QString errorMessage;
    
    static IndexingRun fromJson(const QJsonObject& obj) {
        IndexingRun run;
        run.runId = QUuid(obj["run_id"].toString());
        run.sourceType = obj["source_type"].toString();
        run.status = obj["status"].toString();
        run.scopeJson = obj["scope_json"].toString();
        run.createdAt = QDateTime::fromString(obj["created_at"].toString(), Qt::ISODate);
        run.errorMessage = obj["error_message"].toString();
        return run;
    }
};

#endif // RUNSTATUS_H
