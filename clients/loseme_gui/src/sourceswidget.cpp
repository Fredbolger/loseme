#include "sourceswidget.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QGroupBox>
#include <QHeaderView>
#include <QMessageBox>
#include <QMenu>

// AddSourceDialog implementation
AddSourceDialog::AddSourceDialog(ApiClient* client, QWidget* parent)
    : QDialog(parent), m_apiClient(client) {
    setupUI();
    setWindowTitle("Add Source");
    resize(500, 400);
}

void AddSourceDialog::setupUI() {
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
    
    // Stacked pages
    m_stack = new QStackedWidget(this);
    
    // Filesystem page
    QWidget* fsPage = new QWidget(this);
    QGridLayout* fsLayout = new QGridLayout(fsPage);
    
    fsLayout->addWidget(new QLabel("Directory:"), 0, 0);
    m_fsPath = new QLineEdit(this);
    QPushButton* fsBrowseBtn = new QPushButton("Browse...", this);
    connect(fsBrowseBtn, &QPushButton::clicked, this, &AddSourceDialog::browsePath);
    
    QHBoxLayout* fsPathLayout = new QHBoxLayout;
    fsPathLayout->addWidget(m_fsPath);
    fsPathLayout->addWidget(fsBrowseBtn);
    fsLayout->addLayout(fsPathLayout, 0, 1);
    
    m_fsRecursive = new QCheckBox("Recursive scanning", this);
    m_fsRecursive->setChecked(true);
    fsLayout->addWidget(m_fsRecursive, 1, 0, 1, 2);
    
    // Include patterns
    QGroupBox* incGroup = new QGroupBox("Include Patterns (*.txt, *.md, etc.)", this);
    QVBoxLayout* incLayout = new QVBoxLayout(incGroup);
    m_fsIncludeList = new QListWidget(this);
    incLayout->addWidget(m_fsIncludeList);
    QPushButton* addIncBtn = new QPushButton("Add Pattern", this);
    connect(addIncBtn, &QPushButton::clicked, this, [this]() {
        bool ok;
        QString text = QInputDialog::getText(this, "Add Pattern", "Glob pattern:", QLineEdit::Normal, "*.txt", &ok);
        if (ok && !text.isEmpty()) m_fsIncludeList->addItem(text);
    });
    incLayout->addWidget(addIncBtn);
    fsLayout->addWidget(incGroup, 2, 0, 1, 2);
    
    // Exclude patterns
    QGroupBox* excGroup = new QGroupBox("Exclude Patterns", this);
    QVBoxLayout* excLayout = new QVBoxLayout(excGroup);
    m_fsExcludeList = new QListWidget(this);
    excLayout->addWidget(m_fsExcludeList);
    QPushButton* addExcBtn = new QPushButton("Add Pattern", this);
    connect(addExcBtn, &QPushButton::clicked, this, [this]() {
        bool ok;
        QString text = QInputDialog::getText(this, "Add Pattern", "Glob pattern:", QLineEdit::Normal, "*.log", &ok);
        if (ok && !text.isEmpty()) m_fsExcludeList->addItem(text);
    });
    excLayout->addWidget(addExcBtn);
    fsLayout->addWidget(excGroup, 3, 0, 1, 2);
    
    m_stack->addWidget(fsPage);
    
    // Thunderbird page
    QWidget* tbPage = new QWidget(this);
    QGridLayout* tbLayout = new QGridLayout(tbPage);
    
    tbLayout->addWidget(new QLabel("Mailbox Path:"), 0, 0);
    m_tbPath = new QLineEdit(this);
    QPushButton* tbBrowseBtn = new QPushButton("Browse...", this);
    connect(tbBrowseBtn, &QPushButton::clicked, this, [this]() {
        QString file = QFileDialog::getOpenFileName(this, "Select Mailbox", QString(),
                                                   "All Files (*)");
        if (!file.isEmpty()) m_tbPath->setText(file);
    });
    
    QHBoxLayout* tbPathLayout = new QHBoxLayout;
    tbPathLayout->addWidget(m_tbPath);
    tbPathLayout->addWidget(tbBrowseBtn);
    tbLayout->addLayout(tbPathLayout, 0, 1);
    
    QGroupBox* ignoreGroup = new QGroupBox("Ignore From (email addresses to exclude)", this);
    QVBoxLayout* ignoreLayout = new QVBoxLayout(ignoreGroup);
    m_tbIgnoreList = new QListWidget(this);
    ignoreLayout->addWidget(m_tbIgnoreList);
    QPushButton* addIgnoreBtn = new QPushButton("Add Email", this);
    connect(addIgnoreBtn, &QPushButton::clicked, this, [this]() {
        bool ok;
        QString text = QInputDialog::getText(this, "Add Ignore", "Email address:", QLineEdit::Normal, QString(), &ok);
        if (ok && !text.isEmpty()) m_tbIgnoreList->addItem(text);
    });
    ignoreLayout->addWidget(addIgnoreBtn);
    tbLayout->addWidget(ignoreGroup, 1, 0, 1, 2);
    
    m_stack->addWidget(tbPage);
    mainLayout->addWidget(m_stack);
    
    // Buttons
    QHBoxLayout* btnLayout = new QHBoxLayout;
    btnLayout->addStretch();
    QPushButton* okBtn = new QPushButton("&OK", this);
    QPushButton* cancelBtn = new QPushButton("&Cancel", this);
    btnLayout->addWidget(okBtn);
    btnLayout->addWidget(cancelBtn);
    mainLayout->addLayout(btnLayout);
    
    connect(okBtn, &QPushButton::clicked, this, &AddSourceDialog::validateAndAccept);
    connect(cancelBtn, &QPushButton::clicked, this, &QDialog::reject);
    connect(m_typeCombo, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, &AddSourceDialog::onTypeChanged);
}

void AddSourceDialog::onTypeChanged(int index) {
    m_stack->setCurrentIndex(index);
}

void AddSourceDialog::browsePath() {
    QString dir = QFileDialog::getExistingDirectory(this, "Select Directory", m_fsPath->text());
    if (!dir.isEmpty()) {
        m_fsPath->setText(dir);
    }
}

void AddSourceDialog::validateAndAccept() {
    if (getSourceType() == "filesystem" && m_fsPath->text().isEmpty()) {
        QMessageBox::warning(this, "Validation", "Please select a directory");
        return;
    }
    if (getSourceType() == "thunderbird" && m_tbPath->text().isEmpty()) {
        QMessageBox::warning(this, "Validation", "Please select a mailbox file");
        return;
    }
    accept();
}

QString AddSourceDialog::getSourceType() const {
    return m_typeCombo->currentData().toString();
}

QString AddSourceDialog::getScopeJson() const {
    if (getSourceType() == "filesystem") {
        FilesystemIndexingScope scope;
        scope.directories.append(m_fsPath->text());
        scope.recursive = m_fsRecursive->isChecked();
        
        for (int i = 0; i < m_fsIncludeList->count(); ++i) {
            scope.includePatterns.append(m_fsIncludeList->item(i)->text());
        }
        for (int i = 0; i < m_fsExcludeList->count(); ++i) {
            scope.excludePatterns.append(m_fsExcludeList->item(i)->text());
        }
        return scope.serialize();
        
    } else {
        ThunderbirdIndexingScope scope;
        scope.mboxPath = m_tbPath->text();
        
        for (int i = 0; i < m_tbIgnoreList->count(); ++i) {
            scope.ignorePatterns.append({"from", m_tbIgnoreList->item(i)->text()});
        }
        return scope.serialize();
    }
}

// SourcesWidget implementation
SourcesWidget::SourcesWidget(ApiClient* client, QWidget* parent)
    : QWidget(parent), m_apiClient(client) {
    setupUI();
    refreshSources();
}

void SourcesWidget::setupUI() {
    setWindowTitle("Manage Sources");
    resize(700, 500);
    
    QVBoxLayout* mainLayout = new QVBoxLayout(this);
    
    // Toolbar
    QHBoxLayout* toolbarLayout = new QHBoxLayout;
    m_refreshBtn = new QPushButton("&Refresh", this);
    m_addBtn = new QPushButton("&Add...", this);
    m_scanBtn = new QPushButton("&Scan", this);
    m_toggleBtn = new QPushButton("&Toggle", this);
    m_deleteBtn = new QPushButton("&Delete", this);
    
    toolbarLayout->addWidget(m_refreshBtn);
    toolbarLayout->addWidget(m_addBtn);
    toolbarLayout->addWidget(m_scanBtn);
    toolbarLayout->addWidget(m_toggleBtn);
    toolbarLayout->addWidget(m_deleteBtn);
    toolbarLayout->addStretch();
    
    mainLayout->addLayout(toolbarLayout);
    
    // Tree widget
    m_tree = new QTreeWidget(this);
    m_tree->setColumnCount(4);
    m_tree->setHeaderLabels({"ID", "Type", "Locator", "Enabled"});
    m_tree->setAlternatingRowColors(true);
    m_tree->setContextMenuPolicy(Qt::CustomContextMenu);
    
    mainLayout->addWidget(m_tree);
    
    // Connections
    connect(m_refreshBtn, &QPushButton::clicked, this, &SourcesWidget::refreshSources);
    connect(m_addBtn, &QPushButton::clicked, this, &SourcesWidget::addSource);
    connect(m_scanBtn, &QPushButton::clicked, this, &SourcesWidget::scanSource);
    connect(m_toggleBtn, &QPushButton::clicked, this, &SourcesWidget::toggleSource);
    connect(m_deleteBtn, &QPushButton::clicked, this, &SourcesWidget::deleteSource);
    connect(m_tree, &QTreeWidget::itemDoubleClicked, this, &SourcesWidget::onSourceDoubleClicked);
    connect(m_tree, &QTreeWidget::customContextMenuRequested, this, [this](const QPoint& pos) {
        QMenu menu(this);
        menu.addAction("Scan", this, &SourcesWidget::scanSource);
        menu.addAction("Toggle Enabled", this, &SourcesWidget::toggleSource);
        menu.addSeparator();
        menu.addAction("Delete", this, &SourcesWidget::deleteSource);
        menu.exec(m_tree->mapToGlobal(pos));
    });
}

void SourcesWidget::refreshSources() {
    auto future = m_apiClient->getAllSources();
    
    QFutureWatcher<QJsonArray>* watcher = new QFutureWatcher<QJsonArray>(this);
    connect(watcher, &QFutureWatcher<QJsonArray>::finished, this, [this, watcher]() {
        try {
            m_currentSources = watcher->result();
            populateTree(m_currentSources);
        } catch (const std::exception& e) {
            QMessageBox::critical(this, "Error", QString("Failed to load sources: %1").arg(e.what()));
        }
        watcher->deleteLater();
    });
    watcher->setFuture(future);
}

void SourcesWidget::populateTree(const QJsonArray& sources) {
    m_tree->clear();
    
    for (const auto& val : sources) {
        QJsonObject source = val.toObject();
        QTreeWidgetItem* item = new QTreeWidgetItem(m_tree);
        
        item->setText(0, source["id"].toString());
        item->setText(1, source["source_type"].toString());
        item->setText(2, source["locator"].toString());
        item->setText(3, source["enabled"].toBool() ? "Yes" : "No");
        
        // Add scope details as children
        QJsonObject scope = source["scope"].toObject();
        for (auto it = scope.begin(); it != scope.end(); ++it) {
            QTreeWidgetItem* child = new QTreeWidgetItem(item);
            child->setText(0, QString("  %1: %2").arg(it.key()).arg(it.value().toVariant().toString()));
        }
        
        // Color enabled/disabled
        if (!source["enabled"].toBool()) {
            for (int i = 0; i < 4; ++i) {
                item->setBackground(i, QColor(240, 240, 240));
            }
        }
    }
    
    m_tree->expandAll();
    m_tree->resizeColumnToContents(0);
    m_tree->resizeColumnToContents(1);
}

void SourcesWidget::addSource() {
    AddSourceDialog dialog(m_apiClient, this);
    if (dialog.exec() != QDialog::Accepted) return;
    
    QString type = dialog.getSourceType();
    QString scopeJson = dialog.getScopeJson();
    
    auto future = m_apiClient->addSource(type, scopeJson);
    QFutureWatcher<QUuid>* watcher = new QFutureWatcher<QUuid>(this);
    connect(watcher, &QFutureWatcher<QUuid>::finished, this, [this, watcher]() {
        try {
            QUuid id = watcher->result();
            QMessageBox::information(this, "Success", QString("Added source with ID: %1").arg(id.toString()));
            refreshSources();
        } catch (const std::exception& e) {
            QMessageBox::critical(this, "Error", e.what());
        }
        watcher->deleteLater();
    });
    watcher->setFuture(future);
}

void SourcesWidget::scanSource() {
    auto source = getSourceAt(m_tree->currentIndex().row());
    if (source.isEmpty()) return;
    
    QString sourceType = source["source_type"].toString();
    QJsonObject scope = source["scope"].toObject();
    
    // This would trigger the same logic as ingest dialog but for existing source
    QMessageBox::information(this, "Scan", QString("Would scan source: %1").arg(source["id"].toString()));
    // Implementation would call queue_filesystem_logic or queue_thunderbird_logic equivalent
}

void SourcesWidget::toggleSource() {
    auto source = getSourceAt(m_tree->currentIndex().row());
    if (source.isEmpty()) return;
    
    // Would call API to toggle enabled state
    refreshSources();
}

void SourcesWidget::deleteSource() {
    auto source = getSourceAt(m_tree->currentIndex().row());
    if (source.isEmpty()) return;
    
    QString id = source["id"].toString();
    if (QMessageBox::question(this, "Confirm", QString("Delete source %1?").arg(id)) != QMessageBox::Yes) return;
    
    // Would call API to delete
    refreshSources();
}

void SourcesWidget::onSourceDoubleClicked(QTreeWidgetItem* item, int column) {
    if (!item->parent()) { // Top level item
        scanSource();
    }
}

QJsonObject SourcesWidget::getSourceAt(int index) const {
    if (index < 0 || index >= m_currentSources.size()) return QJsonObject();
    return m_currentSources[index].toObject();
}
