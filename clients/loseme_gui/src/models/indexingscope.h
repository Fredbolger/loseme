#ifndef INDEXINGSCOPE_H
#define INDEXINGSCOPE_H

#include <QString>
#include <QList>
#include <QJsonObject>
#include <QJsonArray>
#include <QVariant>

struct FilesystemIndexingScope {
    QList<QString> directories;
    bool recursive = true;
    QList<QString> includePatterns;
    QList<QString> excludePatterns;
    
    QJsonObject toJson() const {
        QJsonObject obj;
        QJsonArray dirs;
        for (const auto& d : directories) dirs.append(d);
        obj["directories"] = dirs;
        obj["recursive"] = recursive;
        
        QJsonArray inc, exc;
        for (const auto& p : includePatterns) inc.append(p);
        for (const auto& p : excludePatterns) exc.append(p);
        obj["include_patterns"] = inc;
        obj["exclude_patterns"] = exc;
        
        return obj;
    }
    
    static FilesystemIndexingScope fromJson(const QJsonObject& obj) {
        FilesystemIndexingScope scope;
        scope.recursive = obj["recursive"].toBool(true);
        
        QJsonArray dirs = obj["directories"].toArray();
        for (const auto& v : dirs) scope.directories.append(v.toString());
        
        QJsonArray inc = obj["include_patterns"].toArray();
        for (const auto& v : inc) scope.includePatterns.append(v.toString());
        
        QJsonArray exc = obj["exclude_patterns"].toArray();
        for (const auto& v : exc) scope.excludePatterns.append(v.toString());
        
        return scope;
    }
    
    QString serialize() const {
        return QString::fromUtf8(QJsonDocument(toJson()).toJson(QJsonDocument::Compact));
    }
};

struct ThunderbirdIndexingScope {
    QString type = "thunderbird";
    QString mboxPath;
    QList<QPair<QString, QString>> ignorePatterns; // field, value pairs
    
    QJsonObject toJson() const {
        QJsonObject obj;
        obj["type"] = type;
        obj["mbox_path"] = mboxPath;
        
        QJsonArray patterns;
        for (const auto& p : ignorePatterns) {
            QJsonObject pat;
            pat["field"] = p.first;
            pat["value"] = p.second;
            patterns.append(pat);
        }
        obj["ignore_patterns"] = patterns;
        
        return obj;
    }
    
    static ThunderbirdIndexingScope fromJson(const QJsonObject& obj) {
        ThunderbirdIndexingScope scope;
        scope.type = obj["type"].toString("thunderbird");
        scope.mboxPath = obj["mbox_path"].toString();
        
        QJsonArray patterns = obj["ignore_patterns"].toArray();
        for (const auto& v : patterns) {
            QJsonObject pat = v.toObject();
            scope.ignorePatterns.append({pat["field"].toString(), pat["value"].toString()});
        }
        
        return scope;
    }
    
    QString serialize() const {
        return QString::fromUtf8(QJsonDocument(toJson()).toJson(QJsonDocument::Compact));
    }
};

#endif // INDEXINGSCOPE_H
