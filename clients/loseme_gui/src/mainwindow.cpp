#include "mainwindow.h"
#include "sourceswidget.h"
#include "runscontroller.h"
#include <QMenuBar>
#include <QToolBar>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGroupBox>
#include <QSplitter>
#include <QMessageBox>
#include <QDesktopServices>
#include <QUrl>
#include <QFutureWatcher>
#include <QtConcurrent>
#include <QDebug>
#include <QProcess>  // FIX: was missing — QProcess::startDetached used in openSelectedDocument

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent), m_apiClient(new ApiClient(this)) {
    setupUI();
    setupConnections();
    
    setWindowTitle("LoseMe Search Client");
    resize(1200, 800);
}

MainWindow::~MainWindow() = default;

void MainWindow::setupUI() {
    // Menu bar
    QMenu* fileMenu = menuBar()->addMenu("&File");
    m_ingestAction = fileMenu->addAction("&Ingest...", this, &MainWindow::showIngestDialog);
    m_ingestAction->setShortcut(QKeySequence::New);
    fileMenu->addSeparator();

    // FIX: Qt6 removed the addAction(text, receiver, slot, shortcut) 4-argument overload.
    //      Split into addAction + setShortcut.
    QAction* exitAction = fileMenu->addAction("E&xit", this, &QWidget::close);
    exitAction->setShortcut(QKeySequence::Quit);
    
    QMenu* manageMenu = menuBar()->addMenu("&Manage");
    m_sourcesAction = manageMenu->addAction("&Sources...", this, &MainWindow::showSourcesManager);
    m_runsAction = manageMenu->addAction("&Runs...", this, &MainWindow::showRunsManager);
    
    // Central widget with tabs
    m_tabWidget = new QTabWidget(this);
    setCentralWidget(m_tabWidget);
    
    setupSearchTab();
    
    // Status bar
    statusBar()->showMessage("Ready");
    QProgressBar* progress = new QProgressBar(this);
    progress->setMaximumWidth(200);
    progress->setVisible(false);
    statusBar()->addPermanentWidget(progress);
}

void MainWindow::setupSearchTab() {
    m_searchTab = new QWidget(this);
    QVBoxLayout* mainLayout = new QVBoxLayout(m_searchTab);
    
    // Search controls
    QHBoxLayout* searchLayout = new QHBoxLayout;
    m_searchInput = new QLineEdit(this);
    m_searchInput->setPlaceholderText("Enter search query...");
    m_searchInput->setMinimumWidth(400);
    
    m_searchButton = new QPushButton("&Search", this);
    m_searchButton->setDefault(true);
    
    m_topKSpin = new QSpinBox(this);
    m_topKSpin->setRange(1, 100);
    m_topKSpin->setValue(10);
    m_topKSpin->setPrefix("Top ");
    
    m_interactiveCheck = new QCheckBox("Interactive mode", this);
    
    searchLayout->addWidget(m_searchInput, 1);
    searchLayout->addWidget(m_searchButton);
    searchLayout->addWidget(m_topKSpin);
    searchLayout->addWidget(m_interactiveCheck);
    
    mainLayout->addLayout(searchLayout);
    
    // Results and preview splitter
    QSplitter* splitter = new QSplitter(Qt::Horizontal, this);
    
    // Results list
    QGroupBox* resultsGroup = new QGroupBox("Results", this);
    QVBoxLayout* resultsLayout = new QVBoxLayout(resultsGroup);
    m_resultsList = new QListWidget(this);
    m_resultsList->setSelectionMode(QAbstractItemView::SingleSelection);
    resultsLayout->addWidget(m_resultsList);
    splitter->addWidget(resultsGroup);
    
    // Preview pane
    QGroupBox* previewGroup = new QGroupBox("Preview", this);
    QVBoxLayout* previewLayout = new QVBoxLayout(previewGroup);
    m_previewPane = new QTextEdit(this);
    m_previewPane->setReadOnly(true);
    previewLayout->addWidget(m_previewPane);
    splitter->addWidget(previewGroup);
    
    splitter->setSizes({400, 600});
    mainLayout->addWidget(splitter);
    
    m_tabWidget->addTab(m_searchTab, "&Search");
}

void MainWindow::setupConnections() {
    connect(m_searchButton, &QPushButton::clicked, this, &MainWindow::performSearch);
    connect(m_searchInput, &QLineEdit::returnPressed, this, &MainWindow::performSearch);
    connect(m_resultsList, &QListWidget::itemClicked, this, &MainWindow::onSearchResultClicked);
    connect(m_resultsList, &QListWidget::itemDoubleClicked, this, &MainWindow::openSelectedDocument);
}

void MainWindow::performSearch() {
    QString query = m_searchInput->text().trimmed();
    if (query.isEmpty()) return;
    
    m_searchButton->setEnabled(false);
    statusBar()->showMessage("Searching...");
    m_resultsList->clear();
    m_previewPane->clear();
    m_currentResults.clear();
    
    auto future = m_apiClient->search(query, m_topKSpin->value());
    
    QFutureWatcher<QList<SearchResult>>* watcher = new QFutureWatcher<QList<SearchResult>>(this);
    connect(watcher, &QFutureWatcher<QList<SearchResult>>::finished, this, [this, watcher]() {
        try {
            m_currentResults = watcher->result();
            
            if (m_currentResults.isEmpty()) {
                statusBar()->showMessage("No results found", 3000);
                return;
            }
            
            // Fetch full document details
            QList<QUuid> ids;
            for (const auto& r : m_currentResults) ids.append(r.document.documentPartId);
            
            auto docFuture = m_apiClient->batchGetDocuments(ids);
            QFutureWatcher<QList<DocumentPart>>* docWatcher = new QFutureWatcher<QList<DocumentPart>>(this);
            
            connect(docWatcher, &QFutureWatcher<QList<DocumentPart>>::finished, this, [this, docWatcher]() {
                try {
                    auto docs = docWatcher->result();
                    
                    // Update results with full document data
                    for (int i = 0; i < docs.size() && i < m_currentResults.size(); ++i) {
                        m_currentResults[i].document = docs[i];
                        
                        QListWidgetItem* item = new QListWidgetItem(m_resultsList);
                        item->setText(QString("[%1] %2 | score=%3")
                            .arg(i + 1)
                            .arg(docs[i].sourcePath)
                            .arg(m_currentResults[i].score, 0, 'f', 4));
                        item->setData(Qt::UserRole, i);
                        m_resultsList->addItem(item);
                    }
                    
                    statusBar()->showMessage(QString("Found %1 results").arg(docs.size()), 3000);
                } catch (const std::exception& e) {
                    QMessageBox::critical(this, "Error", QString("Failed to fetch documents: %1").arg(e.what()));
                }
                docWatcher->deleteLater();
            });
            
            docWatcher->setFuture(docFuture);
            
        } catch (const std::exception& e) {
            QMessageBox::critical(this, "Search Error", QString("Search failed: %1").arg(e.what()));
            statusBar()->showMessage("Search failed", 3000);
        }
        watcher->deleteLater();
        m_searchButton->setEnabled(true);
    });
    
    watcher->setFuture(future);
}

void MainWindow::onSearchResultClicked(QListWidgetItem* item) {
    int idx = item->data(Qt::UserRole).toInt();
    if (idx < 0 || idx >= m_currentResults.size()) return;
    
    const auto& doc = m_currentResults[idx].document;
    m_previewPane->setPlainText(
        QString("Source: %1\n"
                "Type: %2\n"
                "Content Type: %3\n"
                "Created: %4\n\n"
                "Content:\n%5")
        .arg(doc.sourcePath)
        .arg(doc.contentType)
        .arg(doc.contentType)
        .arg(doc.createdAt.toString())
        .arg(doc.text.left(2000)) // Limit preview
    );
}

void MainWindow::openSelectedDocument() {
    QListWidgetItem* item = m_resultsList->currentItem();
    if (!item) return;
    
    int idx = item->data(Qt::UserRole).toInt();
    const QUuid& id = m_currentResults[idx].document.documentPartId;
    
    auto future = m_apiClient->getOpenDescriptor(id);
    QFutureWatcher<QJsonObject>* watcher = new QFutureWatcher<QJsonObject>(this);
    
    connect(watcher, &QFutureWatcher<QJsonObject>::finished, this, [this, watcher]() {
        try {
            QJsonObject desc = watcher->result();
            QString sourceType = desc["source_type"].toString();
            QString target = desc["target"].toString();
            
            if (sourceType == "filesystem" || sourceType == "url") {
                QDesktopServices::openUrl(QUrl::fromLocalFile(target));
            } else if (sourceType == "thunderbird") {
                // Launch thunderbird with message ID
                QString messageId = target.mid(target.indexOf("<") + 1, 
                                                target.indexOf(">") - target.indexOf("<") - 1);
                QProcess::startDetached("thunderbird", QStringList() << QString("mid:%1").arg(messageId));
            }
        } catch (const std::exception& e) {
            QMessageBox::critical(this, "Error", QString("Failed to open document: %1").arg(e.what()));
        }
        watcher->deleteLater();
    });
    
    watcher->setFuture(future);
}

void MainWindow::showIngestDialog() {
    if (!m_ingestDialog) {
        m_ingestDialog = new IngestDialog(m_apiClient, this);
    }
    m_ingestDialog->show();
    m_ingestDialog->raise();
}

void MainWindow::showSourcesManager() {
    if (!m_sourcesWidget) {
        m_sourcesWidget = new SourcesWidget(m_apiClient, this);
    }
    m_sourcesWidget->show();
    m_sourcesWidget->raise();
}

void MainWindow::showRunsManager() {
    if (!m_runsController) {
        m_runsController = new RunsController(m_apiClient, this);
    }
    m_runsController->show();
    m_runsController->raise();
}

void MainWindow::updateStatus(const QString& message) {
    statusBar()->showMessage(message, 5000);
}
