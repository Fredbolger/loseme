#include "runscontroller.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QHeaderView>
#include <QMessageBox>
#include <QMenu>
#include <QAction>

RunsController::RunsController(ApiClient* client, QWidget* parent)
    : QWidget(parent)
    , m_apiClient(client)
    , m_refreshTimer(new QTimer(this)) {
    
    setupUI();
    
    m_refreshTimer->setInterval(5000); // 5 second auto-refresh
    connect(m_refreshTimer, &QTimer::timeout, this, &RunsController::autoRefresh);
    
    refreshRuns();
}

void RunsController::setupUI() {
    setWindowTitle("Manage Runs");
    resize(800, 400);
    
    QVBoxLayout* mainLayout = new QVBoxLayout(this);
    
    // Toolbar
    QHBoxLayout* toolbarLayout = new QHBoxLayout;
    
    m_refreshBtn = new QPushButton("&Refresh", this);
    m_stopBtn = new QPushButton("&Stop Selected", this);
    m_stopLatestBtn = new QPushButton("Stop &Latest", this);
    m_resumeBtn = new QPushButton("&Resume Latest", this);
    
    m_autoRefreshCheck = new QCheckBox("Auto-refresh", this);
    m_autoRefreshCheck->setChecked(false);
    
    toolbarLayout->addWidget(m_refreshBtn);
    toolbarLayout->addWidget(m_stopBtn);
    toolbarLayout->addWidget(m_stopLatestBtn);
    toolbarLayout->addWidget(m_resumeBtn);
    toolbarLayout->addStretch();
    toolbarLayout->addWidget(m_autoRefreshCheck);
    
    mainLayout->addLayout(toolbarLayout);
    
    // Table
    m_table = new QTableWidget(this);
    m_table->setColumnCount(5);
    m_table->setHorizontalHeaderLabels({"Run ID", "Source Type", "Status", "Created", "Error"});
    m_table->setSelectionBehavior(QAbstractItemView::SelectRows);
    m_table->setSelectionMode(QAbstractItemView::SingleSelection);
    m_table->setAlternatingRowColors(true);
    m_table->horizontalHeader()->setStretchLastSection(true);
    m_table->setContextMenuPolicy(Qt::CustomContextMenu);
    
    mainLayout->addWidget(m_table);
    
    // Connections
    connect(m_refreshBtn, &QPushButton::clicked, this, &RunsController::refreshRuns);
    connect(m_stopBtn, &QPushButton::clicked, this, &RunsController::stopSelected);
    connect(m_stopLatestBtn, &QPushButton::clicked, this, &RunsController::stopLatest);
    connect(m_resumeBtn, &QPushButton::clicked, this, &RunsController::resumeLatest);
    connect(m_autoRefreshCheck, &QCheckBox::toggled, this, [this](bool checked) {
        if (checked) m_refreshTimer->start();
        else m_refreshTimer->stop();
    });
    connect(m_table, &QTableWidget::customContextMenuRequested, this, [this](const QPoint& pos) {
        QMenu menu(this);
        menu.addAction("Copy ID", this, [this]() {
            auto item = m_table->currentItem();
            if (item) QApplication::clipboard()->setText(item->text());
        });
        menu.addAction("View Details", this, [this]() {
            // Show detailed run info dialog
        });
        menu.exec(m_table->mapToGlobal(pos));
    });
}

void RunsController::refreshRuns() {
    auto future = m_apiClient->listRuns();
    
    QFutureWatcher<QList<IndexingRun>>* watcher = new QFutureWatcher<QList<IndexingRun>>(this);
    connect(watcher, &QFutureWatcher<QList<IndexingRun>>::finished, this, [this, watcher]() {
        try {
            auto runs = watcher->result();
            updateTable(runs);
        } catch (const std::exception& e) {
            QMessageBox::critical(this, "Error", QString("Failed to load runs: %1").arg(e.what()));
        }
        watcher->deleteLater();
    });
    watcher->setFuture(future);
}

void RunsController::updateTable(const QList<IndexingRun>& runs) {
    m_table->setRowCount(runs.size());
    
    for (int i = 0; i < runs.size(); ++i) {
        const auto& run = runs[i];
        
        m_table->setItem(i, 0, new QTableWidgetItem(run.runId.toString()));
        m_table->setItem(i, 1, new QTableWidgetItem(run.sourceType));
        
        QTableWidgetItem* statusItem = new QTableWidgetItem(run.status);
        // Color code status
        if (run.status == "completed") statusItem->setBackground(QColor(200, 255, 200));
        else if (run.status == "failed") statusItem->setBackground(QColor(255, 200, 200));
        else if (run.status == "indexing") statusItem->setBackground(QColor(200, 200, 255));
        m_table->setItem(i, 2, statusItem);
        
        m_table->setItem(i, 3, new QTableWidgetItem(run.createdAt.toString()));
        m_table->setItem(i, 4, new QTableWidgetItem(run.errorMessage));
    }
    
    m_table->resizeColumnsToContents();
}

void RunsController::stopSelected() {
    int row = m_table->currentRow();
    if (row < 0) return;
    
    QUuid runId(m_table->item(row, 0)->text());
    
    auto future = m_apiClient->requestStop(runId);
    QFutureWatcher<void>* watcher = new QFutureWatcher<void>(this);
    connect(watcher, &QFutureWatcher<void>::finished, this, [this, watcher]() {
        watcher->deleteLater();
        refreshRuns();
    });
    watcher->setFuture(future);
}

void RunsController::stopLatest() {
    QString sourceType = QInputDialog::getText(this, "Stop Latest", "Source type (filesystem/thunderbird):");
    if (sourceType.isEmpty()) return;
    
    auto future = m_apiClient->stopLatest(sourceType);
    QFutureWatcher<IndexingRun>* watcher = new QFutureWatcher<IndexingRun>(this);
    connect(watcher, &QFutureWatcher<IndexingRun>::finished, this, [this, watcher]() {
        try {
            auto run = watcher->result();
            QMessageBox::information(this, "Stopped", QString("Stopped run %1").arg(run.runId.toString()));
            refreshRuns();
        } catch (const std::exception& e) {
            QMessageBox::critical(this, "Error", e.what());
        }
        watcher->deleteLater();
    });
    watcher->setFuture(future);
}

void RunsController::resumeLatest() {
    QString sourceType = QInputDialog::getText(this, "Resume Latest", "Source type (filesystem/thunderbird):");
    if (sourceType.isEmpty()) return;
    
    auto future = m_apiClient->resumeLatest(sourceType);
    QFutureWatcher<IndexingRun>* watcher = new QFutureWatcher<IndexingRun>(this);
    connect(watcher, &QFutureWatcher<IndexingRun>::finished, this, [this, watcher]() {
        try {
            auto run = watcher->result();
            if (run.runId.isNull()) {
                QMessageBox::information(this, "No Run", "No interrupted run found");
            } else {
                QMessageBox::information(this, "Resumed", QString("Resuming run %1").arg(run.runId.toString()));
                refreshRuns();
            }
        } catch (const std::exception& e) {
            QMessageBox::critical(this, "Error", e.what());
        }
        watcher->deleteLater();
    });
    watcher->setFuture(future);
}

void RunsController::autoRefresh() {
    if (isVisible()) {
        refreshRuns();
    }
}
