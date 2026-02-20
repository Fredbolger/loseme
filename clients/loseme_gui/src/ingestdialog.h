#ifndef INGESTDIALOG_H
#define INGESTDIALOG_H

#include <QDialog>
#include <QStackedWidget>
#include <QLineEdit>
#include <QCheckBox>
#include <QListWidget>
#include <QPushButton>
#include <QProgressBar>
#include <QLabel>
#include <QComboBox>
#include <QThread>
#include "apiclient.h"

class IngestWorker : public QObject {
    Q_OBJECT
public:
    IngestWorker(ApiClient* client, const QString& type, const QVariantMap& config);
    
public slots:
    void start();
    void stop();
    
signals:
    void progress(const QString& message);
    void documentQueued(const QString& path);
    void finished(bool success, const QString& error);
    void discoveryCompleted();
    
private:
    ApiClient* m_client;
    QString m_type;
    QVariantMap m_config;
    bool m_shouldStop = false;
    QUuid m_currentRunId;
    
    void runFilesystem();
    void runThunderbird();
    void queueDocumentPartWithRetry(const DocumentPart& part, const QString& scopeJson);
};

class IngestDialog : public QDialog {
    Q_OBJECT

public:
    explicit IngestDialog(ApiClient* client, QWidget* parent = nullptr);

private slots:
    void onTypeChanged(int index);
    void browseFilesystem();
    void browseThunderbird();
    void startIngestion();
    void stopIngestion();
    void onProgress(const QString& message);
    void onDocumentQueued(const QString& path);
    void onFinished(bool success, const QString& error);
    void onDiscoveryCompleted();

private:
    void setupUI();
    
    ApiClient* m_apiClient;
    QThread* m_workerThread;
    IngestWorker* m_worker;
    
    // Type selection
    QComboBox* m_typeCombo;
    QStackedWidget* m_stack;
    
    // Filesystem page
    QLineEdit* m_fsPathEdit;
    QPushButton* m_fsBrowseBtn;
    QCheckBox* m_fsRecursiveCheck;
    QListWidget* m_fsIncludeList;
    QListWidget* m_fsExcludeList;
    QPushButton* m_fsAddIncludeBtn;
    QPushButton* m_fsAddExcludeBtn;
    
    // Thunderbird page
    QLineEdit* m_tbPathEdit;
    QPushButton* m_tbBrowseBtn;
    QListWidget* m_tbIgnoreList;
    QPushButton* m_tbAddIgnoreBtn;
    
    // Progress
    QProgressBar* m_progressBar;
    QLabel* m_statusLabel;
    QListWidget* m_logList;
    QPushButton* m_startBtn;
    QPushButton* m_stopBtn;
    QPushButton* m_closeBtn;
};

#endif // INGESTDIALOG_H
