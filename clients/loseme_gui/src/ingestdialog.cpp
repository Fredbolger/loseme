#include "ingestdialog.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QGroupBox>
#include <QFileDialog>
#include <QMessageBox>
#include <QInputDialog>
#include <QFutureWatcher>
#include <QtConcurrent>

// IngestWorker implementation
IngestWorker::IngestWorker(ApiClient* client, const QString& type, const QVariantMap& config)
    : m_client(client), m_type(type), m_config(config) {}

void IngestWorker::start() {
    if (m_type == "filesystem") {
        runFilesystem();
    } else if (m_type == "thunderbird") {
        runThunderbird();
    }
}

void IngestWorker::stop() {
    m_shouldStop = true;
    if (!m_currentRunId.isNull()) {
        auto future = m_client->requestStop(m_currentRunId);
        future.waitForFinished();
    }
}

void IngestWorker::runFilesystem() {
    QString path = m_config["path"].toString();
    bool recursive = m_config["recursive"].toBool();
    QStringList includes = m_config["includes"].toStringList();
    QStringList excludes = m_config["excludes"].toStringList();
    
    FilesystemIndexingScope scope;
    scope.directories.append(path);
    scope.recursive = recursive;
    scope.includePatterns = includes;
    scope.excludePatterns = excludes;
    
    emit progress("Creating indexing run...");
    
    try {
        auto future = m_client->createRun("filesystem", scope.serialize());
        future.waitForFinished();
        m_currentRunId = future.result();
        
        emit progress(QString("Started run %1").arg(m_currentRunId.toString()));
        
        auto startFuture = m_client->startIndexing(m_currentRunId);
        startFuture.waitForFinished();
        
        // Simulate document discovery (in real impl, use actual FilesystemIngestionSource)
        // Here we recursively scan and queue files
        QDirIterator it(path, includes.isEmpty() ? QStringList() : includes, 
                       QDir::Files, recursive ? QDirIterator::Subdirectories : QDirIterator::NoIteratorFlags);
        
        int count = 0;
        while (it.hasNext() && !m_shouldStop) {
            QString filePath = it.next();
            
            // Check excludes
            bool excluded = false;
            for (const auto& pattern : excludes) {
                QRegularExpression regex(QRegularExpression::wildcardToRegularExpression(pattern));
                if (regex.match(filePath).hasMatch()) {
                    excluded = true;
                    break;
                }
            }
            if (excluded) continue;
            
            // Create document part
            DocumentPart part;
            part.documentPartId = QUuid::createUuid();
            part.sourceType = "filesystem";
            part.sourcePath = filePath;
            part.sourceInstanceId = QString("%1|%2").arg(QSysInfo::machineHostName()).arg(path);
            part.unitLocator = filePath;
            part.contentType = "text/plain";
            part.createdAt = QDateTime::currentDateTime();
            part.updatedAt = part.createdAt;
            
            // Read file content (simplified - real impl would use proper extractors)
            QFile file(filePath);
            if (file.open(QIODevice::ReadOnly | QIODevice::Text)) {
                part.text = QString::fromUtf8(file.readAll()).left(10000); // Limit size
                file.close();
            }
            
            queueDocumentPartWithRetry(part, scope.serialize());
            
            emit documentQueued(filePath);
            if (++count % 10 == 0) {
                emit progress(QString("Queued %1 documents...").arg(count));
            }
            
            // Check stop requested periodically
            if (count % 50 == 0) {
                auto stopFuture = m_client->isStopRequested(m_currentRunId);
                stopFuture.waitForFinished();
                if (stopFuture.result()) {
                    m_shouldStop = true;
                    break;
                }
            }
        }
        
        if (m_shouldStop) {
            emit progress("Stop requested, terminating...");
            m_client->markFailed(m_currentRunId, "User requested stop").waitForFinished();
            emit finished(false, "Stopped by user");
        } else {
            m_client->discoveringStopped(m_currentRunId).waitForFinished();
            emit discoveryCompleted();
            emit finished(true, QString("Completed. Queued %1 documents").arg(count));
        }
        
    } catch (const std::exception& e) {
        if (!m_currentRunId.isNull()) {
            m_client->markFailed(m_currentRunId, e.what()).waitForFinished();
        }
        emit finished(false, e.what());
    }
}

void IngestWorker::runThunderbird() {
    QString mboxPath = m_config["mbox_path"].toString();
    QStringList ignoreFrom = m_config["ignore_from"].toStringList();
    
    ThunderbirdIndexingScope scope;
    scope.mboxPath = mboxPath;
    for (const auto& val : ignoreFrom) {
        scope.ignorePatterns.append({"from", val});
    }
    
    emit progress("Creating Thunderbird indexing run...");
    
    try {
        auto future = m_client->createRun("thunderbird", scope.serialize());
        future.waitForFinished();
        m_currentRunId = future.result();
        
        emit progress(QString("Started run %1").arg(m_currentRunId.toString()));
        
        auto startFuture = m_client->startIndexing(m_currentRunId);
        startFuture.waitForFinished();
        
        // Parse mbox file (simplified - real impl would use proper mbox parser)
        QFile mbox(mboxPath);
        if (!mbox.open(QIODevice::ReadOnly | QIODevice::Text)) {
            throw std::runtime_error("Cannot open mbox file");
        }
        
        int count = 0;
        QString currentMessage;
        while (!mbox.atEnd() && !m_shouldStop) {
            QString line = QString::fromUtf8(mbox.readLine());
            
            if (line.startsWith("From ") && !currentMessage.isEmpty()) {
                // Process previous message
                DocumentPart part;
                part.documentPartId = QUuid::createUuid();
                part.sourceType = "thunderbird";
                part.sourcePath = QString("INBOX/<%1>").arg(part.documentPartId.toString());
                part.sourceInstanceId = QString("%1|%2").arg(QSysInfo::machineHostName()).arg(mboxPath);
                part.unitLocator = part.sourcePath;
                part.contentType = "message/rfc822";
                part.text = currentMessage;
                part.createdAt = QDateTime::currentDateTime();
                part.updatedAt = part.createdAt;
                
                // Check ignore patterns (simplified)
                bool ignored = false;
                for (const auto& pat : ignoreFrom) {
                    if (currentMessage.contains(QString("From: %1").arg(pat))) {
                        ignored = true;
                        break;
                    }
                }
                
                if (!ignored) {
                    queueDocumentPartWithRetry(part, scope.serialize());
                    emit documentQueued(part.sourcePath);
                    if (++count % 10 == 0) {
                        emit progress(QString("Queued %1 emails...").arg(count));
                    }
                }
                
                currentMessage.clear();
            }
            currentMessage += line;
        }
        
        mbox.close();
        
        if (m_shouldStop) {
            m_client->markFailed(m_currentRunId, "User requested stop").waitForFinished();
            emit finished(false, "Stopped by user");
        } else {
            m_client->discoveringStopped(m_currentRunId).waitForFinished();
            emit discoveryCompleted();
            emit finished(true, QString("Completed. Queued %1 emails").arg(count));
        }
        
    } catch (const std::exception& e) {
        if (!m_currentRunId.isNull()) {
            m_client->markFailed(m_currentRunId, e.what()).waitForFinished();
        }
        emit finished(false, e.what());
    }
}

void IngestWorker::queueDocumentPartWithRetry(const DocumentPart& part, const QString& scopeJson) {
    const int maxRetries = 3;
    for (int i = 0; i < maxRetries; ++i) {
        try {
            auto future = m_client->queueDocumentPart(m_currentRunId, part, scopeJson);
            future.waitForFinished();
            future.result(); // Will throw if error
            return;
        } catch (...) {
            if (i == maxRetries - 1) throw;
            QThread::msleep(100 * (i + 1)); // Exponential backoff
        }
    }
}

// IngestDialog implementation
IngestDialog::IngestDialog(ApiClient* client, QWidget* parent)
    : QDialog(parent), m_apiClient(client), m_worker(nullptr), m_workerThread(nullptr) {
    setupUI();
    setWindowTitle("Ingest Documents");
    resize(600, 500);
}

void IngestDialog::setupUI() {
    QVBoxLayout* mainLayout = new QVBoxLayout(this);
    
    // Type selection
    QHBoxLayout* typeLayout = new QHBoxLayout;
    typeLayout->addWidget(new QLabel("Source Type:"));
    m_typeCombo = new QComboBox(this);
    m_typeCombo->addItem("Filesystem", "filesystem");
    m_typeCombo->addItem("Thunderbird", "thunderbird");
    typeLayout->addWidget(m_typeCombo);
    typeLayout->addStretch();
    mainLayout->addLayout(typeLayout);
    
    // Stacked widget for different types
    m_stack = new QStackedWidget(this);
    
    // Filesystem page
    QWidget* fsPage = new QWidget(this);
    QGridLayout* fsLayout = new QGridLayout(fsPage);
    
    fsLayout->addWidget(new QLabel("Directory:"), 0, 0);
    m_fsPathEdit = new QLineEdit(this);
    m_fsBrowseBtn = new QPushButton("Browse...", this);
    QHBoxLayout* fsPathLayout = new QHBoxLayout;
    fsPathLayout->addWidget(m_fsPathEdit);
    fsPathLayout->addWidget(m_fsBrowseBtn);
    fsLayout->addLayout(fsPathLayout, 0, 1);
    
    m_fsRecursiveCheck = new QCheckBox("Recursive", this);
    m_fsRecursiveCheck->setChecked(true);
    fsLayout->addWidget(m_fsRecursiveCheck, 1, 0, 1, 2);
    
    // Include patterns
    QGroupBox* incGroup = new QGroupBox("Include Patterns", this);
    QVBoxLayout* incLayout = new QVBoxLayout(incGroup);
    m_fsIncludeList = new QListWidget(this);
    incLayout->addWidget(m_fsIncludeList);
    m_fsAddIncludeBtn = new QPushButton("Add Pattern...", this);
    incLayout->addWidget(m_fsAddIncludeBtn);
    fsLayout->addWidget(incGroup, 2, 0, 1, 2);
    
    // Exclude patterns
    QGroupBox* excGroup = new QGroupBox("Exclude Patterns", this);
    QVBoxLayout* excLayout = new QVBoxLayout(excGroup);
    m_fsExcludeList = new QListWidget(this);
    excLayout->addWidget(m_fsExcludeList);
    m_fsAddExcludeBtn = new QPushButton("Add Pattern...", this);
    excLayout->addWidget(m_fsAddExcludeBtn);
    fsLayout->addWidget(excGroup, 3, 0, 1, 2);
    
    m_stack->addWidget(fsPage);
    
    // Thunderbird page
    QWidget* tbPage = new QWidget(this);
    QGridLayout* tbLayout = new QGridLayout(tbPage);
    
    tbLayout->addWidget(new QLabel("Mailbox:"), 0, 0);
    m_tbPathEdit = new QLineEdit(this);
    m_tbBrowseBtn = new QPushButton("Browse...", this);
    QHBoxLayout* tbPathLayout = new QHBoxLayout;
    tbPathLayout->addWidget(m_tbPathEdit);
    tbPathLayout->addWidget(m_tbBrowseBtn);
    tbLayout->addLayout(tbPathLayout, 0, 1);
    
    QGroupBox* ignoreGroup = new QGroupBox("Ignore From", this);
    QVBoxLayout* ignoreLayout = new QVBoxLayout(ignoreGroup);
    m_tbIgnoreList = new QListWidget(this);
    ignoreLayout->addWidget(m_tbIgnoreList);
    m_tbAddIgnoreBtn = new QPushButton("Add Email...", this);
    ignoreLayout->addWidget(m_tbAddIgnoreBtn);
    tbLayout->addWidget(ignoreGroup, 1, 0, 1, 2);
    
    m_stack->addWidget(tbPage);
    mainLayout->addWidget(m_stack);
    
    // Progress section
    QGroupBox* progressGroup = new QGroupBox("Progress", this);
    QVBoxLayout* progressLayout = new QVBoxLayout(progressGroup);
    
    m_statusLabel = new QLabel("Ready", this);
    progressLayout->addWidget(m_statusLabel);
    
    m_progressBar = new QProgressBar(this);
    m_progressBar->setRange(0, 0); // Indeterminate
    m_progressBar->setVisible(false);
    progressLayout->addWidget(m_progressBar);
    
    m_logList = new QListWidget(this);
    m_logList->setMaximumHeight(150);
    progressLayout->addWidget(m_logList);
    
    mainLayout->addWidget(progressGroup);
    
    // Buttons
    QHBoxLayout* btnLayout = new QHBoxLayout;
    btnLayout->addStretch();
    m_startBtn = new QPushButton("&Start", this);
    m_startBtn->setDefault(true);
    m_stopBtn = new QPushButton("S&top", this);
    m_stopBtn->setEnabled(false);
    m_closeBtn = new QPushButton("&Close", this);
    btnLayout->addWidget(m_startBtn);
    btnLayout->addWidget(m_stopBtn);
    btnLayout->addWidget(m_closeBtn);
    mainLayout->addLayout(btnLayout);
    
    // Connections
    connect(m_typeCombo, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, &IngestDialog::onTypeChanged);
    connect(m_fsBrowseBtn, &QPushButton::clicked, this, &IngestDialog::browseFilesystem);
    connect(m_tbBrowseBtn, &QPushButton::clicked, this, &IngestDialog::browseThunderbird);
    connect(m_fsAddIncludeBtn, &QPushButton::clicked, this, [this]() {
        bool ok;
        QString text = QInputDialog::getText(this, "Add Pattern", "Glob pattern (e.g. *.txt):", QLineEdit::Normal, "", &ok);
        if (ok && !text.isEmpty()) m_fsIncludeList->addItem(text);
    });
    connect(m_fsAddExcludeBtn, &QPushButton::clicked, this, [this]() {
        bool ok;
        QString text = QInputDialog::getText(this, "Add Pattern", "Glob pattern (e.g. *.log):", QLineEdit::Normal, "", &ok);
        if (ok && !text.isEmpty()) m_fsExcludeList->addItem(text);
    });
    connect(m_tbAddIgnoreBtn, &QPushButton::clicked, this, [this]() {
        bool ok;
        QString text = QInputDialog::getText(this, "Add Ignore", "Email address to ignore:", QLineEdit::Normal, "", &ok);
        if (ok && !text.isEmpty()) m_tbIgnoreList->addItem(text);
    });
    connect(m_startBtn, &QPushButton::clicked, this, &IngestDialog::startIngestion);
    connect(m_stopBtn, &QPushButton::clicked, this, &IngestDialog::stopIngestion);
    connect(m_closeBtn, &QPushButton::clicked, this, &QDialog::close);
}

void IngestDialog::onTypeChanged(int index) {
    m_stack->setCurrentIndex(index);
}

void IngestDialog::browseFilesystem() {
    QString dir = QFileDialog::getExistingDirectory(this, "Select Directory", m_fsPathEdit->text());
    if (!dir.isEmpty()) {
        m_fsPathEdit->setText(dir);
    }
}

void IngestDialog::browseThunderbird() {
    QString file = QFileDialog::getOpenFileName(this, "Select Mailbox", m_tbPathEdit->text(),
                                               "Mbox Files (*);;All Files (*)");
    if (!file.isEmpty()) {
        m_tbPathEdit->setText(file);
    }
}

void IngestDialog::startIngestion() {
    QVariantMap config;
    QString type = m_typeCombo->currentData().toString();
    
    if (type == "filesystem") {
        if (m_fsPathEdit->text().isEmpty()) {
            QMessageBox::warning(this, "Error", "Please select a directory");
            return;
        }
        config["path"] = m_fsPathEdit->text();
        config["recursive"] = m_fsRecursiveCheck->isChecked();
        
        QStringList includes;
        for (int i = 0; i < m_fsIncludeList->count(); ++i) includes.append(m_fsIncludeList->item(i)->text());
        config["includes"] = includes;
        
        QStringList excludes;
        for (int i = 0; i < m_fsExcludeList->count(); ++i) excludes.append(m_fsExcludeList->item(i)->text());
        config["excludes"] = excludes;
        
    } else if (type == "thunderbird") {
        if (m_tbPathEdit->text().isEmpty()) {
            QMessageBox::warning(this, "Error", "Please select a mailbox");
            return;
        }
        config["mbox_path"] = m_tbPathEdit->text();
        
        QStringList ignores;
        for (int i = 0; i < m_tbIgnoreList->count(); ++i) ignores.append(m_tbIgnoreList->item(i)->text());
        config["ignore_from"] = ignores;
    }
    
    m_startBtn->setEnabled(false);
    m_stopBtn->setEnabled(true);
    m_progressBar->setVisible(true);
    m_logList->clear();
    
    m_workerThread = new QThread(this);
    m_worker = new IngestWorker(m_apiClient, type, config);
    m_worker->moveToThread(m_workerThread);
    
    connect(m_workerThread, &QThread::started, m_worker, &IngestWorker::start);
    connect(m_worker, &IngestWorker::progress, this, &IngestDialog::onProgress);
    connect(m_worker, &IngestWorker::documentQueued, this, &IngestDialog::onDocumentQueued);
    connect(m_worker, &IngestWorker::finished, this, &IngestDialog::onFinished);
    connect(m_worker, &IngestWorker::discoveryCompleted, this, &IngestDialog::onDiscoveryCompleted);
    
    m_workerThread->start();
}

void IngestDialog::stopIngestion() {
    if (m_worker) {
        m_worker->stop();
    }
    m_stopBtn->setEnabled(false);
}

void IngestDialog::onProgress(const QString& message) {
    m_statusLabel->setText(message);
    m_logList->addItem(message);
    m_logList->scrollToBottom();
}

void IngestDialog::onDocumentQueued(const QString& path) {
    m_logList->addItem(QString("  -> %1").arg(path));
    if (m_logList->count() > 100) {
        delete m_logList->takeItem(0); // Limit log size
    }
    m_logList->scrollToBottom();
}

void IngestDialog::onFinished(bool success, const QString& error) {
    m_progressBar->setVisible(false);
    m_startBtn->setEnabled(true);
    m_stopBtn->setEnabled(false);
    
    if (success) {
        m_statusLabel->setText(QString("Completed: %1").arg(error));
        QMessageBox::information(this, "Success", error);
    } else {
        m_statusLabel->setText(QString("Failed: %1").arg(error));
        QMessageBox::critical(this, "Error", error);
    }
    
    if (m_workerThread) {
        m_workerThread->quit();
        m_workerThread->wait();
        delete m_workerThread;
        m_workerThread = nullptr;
    }
    m_worker = nullptr;
}

void IngestDialog::onDiscoveryCompleted() {
    m_statusLabel->setText("Discovery completed, finalizing...");
}
