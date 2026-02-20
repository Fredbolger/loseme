#include "searchwidget.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QGroupBox>
#include <QHeaderView>
#include <QClipboard>
#include <QApplication>
#include <QDesktopServices>
#include <QUrl>
#include <QFileInfo>
#include <QDir>
#include <QMessageBox>
#include <QFileDialog>
#include <QPainter>
#include <QTextDocument>
#include <QScrollBar>
#include <QKeyEvent>
#include <QProcess>

// SearchResultsModel implementation
SearchResultsModel::SearchResultsModel(QObject* parent) 
    : QStandardItemModel(parent) {
    setColumnCount(1);
}

void SearchResultsModel::setResults(const QList<SearchResult>& results) {
    clear();
    m_results = results;
    
    for (int i = 0; i < results.size(); ++i) {
        const auto& result = results[i];
        QStandardItem* item = new QStandardItem();
        
        item->setData(result.document.documentPartId.toString(), Qt::DisplayRole);
        item->setData(QVariant::fromValue(result), DocumentPartRole);
        item->setData(result.score, ScoreRole);
        item->setData(result.document.text, FullTextRole);
        
        // Store document data for display
        item->setData(result.document.sourcePath, Qt::ToolTipRole);
        item->setData(result.document.contentType, Qt::UserRole + 10);
        item->setData(result.document.createdAt, Qt::UserRole + 11);
        
        appendRow(item);
    }
}

QList<SearchResult> SearchResultsModel::getResults() const {
    return m_results;
}

SearchResult SearchResultsModel::getResultAt(int index) const {
    if (index >= 0 && index < m_results.size()) {
        return m_results[index];
    }
    return SearchResult();
}

void SearchResultsModel::clearResults() {
    clear();
    m_results.clear();
}

// SearchResultDelegate implementation
SearchResultDelegate::SearchResultDelegate(QObject* parent) 
    : QStyledItemDelegate(parent) {}

void SearchResultDelegate::paint(QPainter* painter, const QStyleOptionViewItem& option, 
                                const QModelIndex& index) const {
    QStyleOptionViewItem opt = option;
    initStyleOption(&opt, index);
    
    painter->save();
    
    // Background
    if (opt.state & QStyle::State_Selected) {
        painter->fillRect(opt.rect, opt.palette.highlight());
    } else if (opt.state & QStyle::State_MouseOver) {
        painter->fillRect(opt.rect, opt.palette.alternateBase());
    } else {
        painter->fillRect(opt.rect, opt.palette.base());
    }
    
    // Get data
    double score = index.data(SearchResultsModel::ScoreRole).toDouble();
    QString sourcePath = index.data(Qt::ToolTipRole).toString();
    QString contentType = index.data(Qt::UserRole + 10).toString();
    QDateTime createdAt = index.data(Qt::UserRole + 11).toDateTime();
    
    // Layout calculations
    int margin = 5;
    int textHeight = opt.fontMetrics.height();
    QRect textRect = opt.rect.adjusted(margin, margin, -margin, -margin);
    
    // Score indicator (left side colored bar)
    int scoreBarWidth = 4;
    QColor scoreColor = scoreToColor(score);
    painter->fillRect(opt.rect.left(), opt.rect.top(), scoreBarWidth, opt.rect.height(), scoreColor);
    
    textRect.adjust(scoreBarWidth + margin, 0, 0, 0);
    
    // Title (source path)
    QFont titleFont = opt.font;
    titleFont.setBold(true);
    painter->setFont(titleFont);
    painter->setPen(opt.state & QStyle::State_Selected ? opt.palette.highlightedText().color() 
                                                       : opt.palette.text().color());
    
    QString elidedPath = opt.fontMetrics.elidedText(sourcePath, Qt::ElideMiddle, textRect.width());
    painter->drawText(textRect, Qt::AlignLeft | Qt::AlignTop, elidedPath);
    
    // Metadata line
    textRect.adjust(0, textHeight + 2, 0, 0);
    QFont metaFont = opt.font;
    metaFont.setPointSize(opt.font.pointSize() - 1);
    painter->setFont(metaFont);
    painter->setPen(opt.state & QStyle::State_Selected ? opt.palette.highlightedText().color().lighter() 
                                                       : opt.palette.text().color().lighter());
    
    QString meta = QString("Score: %1 | %2 | %3")
        .arg(score, 0, 'f', 4)
        .arg(contentType)
        .arg(createdAt.toString("yyyy-MM-dd hh:mm"));
    painter->drawText(textRect, Qt::AlignLeft | Qt::AlignTop, meta);
    
    painter->restore();
}

QSize SearchResultDelegate::sizeHint(const QStyleOptionViewItem& option, 
                                    const QModelIndex& index) const {
    int height = option.fontMetrics.height() * 2 + 14;  // Two lines + margins
    return QSize(200, height);
}

QColor SearchResultDelegate::scoreToColor(double score) const {
    // Gradient from red (low) to green (high)
    if (score > 0.8) return QColor(46, 204, 113);      // Green
    if (score > 0.6) return QColor(241, 196, 15);       // Yellow
    if (score > 0.4) return QColor(230, 126, 34);       // Orange
    return QColor(231, 76, 60);                         // Red
}

// SearchHighlighter implementation
SearchHighlighter::SearchHighlighter(QTextDocument* parent) 
    : QSyntaxHighlighter(parent) {}

void SearchHighlighter::setSearchTerms(const QStringList& terms) {
    m_searchTerms = terms;
    m_formats.clear();
    
    // Generate different highlight colors for different terms
    QList<QColor> colors = {
        QColor(255, 255, 0, 128),    // Yellow
        QColor(0, 255, 0, 128),      // Green
        QColor(0, 255, 255, 128),    // Cyan
        QColor(255, 192, 203, 128),  // Pink
        QColor(255, 165, 0, 128)     // Orange
    };
    
    for (int i = 0; i < terms.size(); ++i) {
        QTextCharFormat format;
        format.setBackground(colors[i % colors.size()]);
        format.setFontWeight(QFont::Bold);
        m_formats.append(format);
    }
    
    rehighlight();
}

void SearchHighlighter::clearHighlight() {
    m_searchTerms.clear();
    m_formats.clear();
    rehighlight();
}

void SearchHighlighter::highlightBlock(const QString& text) {
    for (int i = 0; i < m_searchTerms.size(); ++i) {
        const QString& term = m_searchTerms[i];
        if (term.isEmpty()) continue;
        
        int index = text.indexOf(term, 0, Qt::CaseInsensitive);
        while (index >= 0) {
            int length = term.length();
            setFormat(index, length, m_formats[i]);
            index = text.indexOf(term, index + length, Qt::CaseInsensitive);
        }
    }
}

// SearchWidget implementation
SearchWidget::SearchWidget(ApiClient* client, QWidget* parent)
    : QWidget(parent)
    , m_apiClient(client)
    , m_isSearching(false)
    , m_liveSearchTimer(new QTimer(this))
    , m_searchWatcher(nullptr)
    , m_docsWatcher(nullptr)
    , m_openWatcher(nullptr) {
    
    setupUI();
    setupConnections();
    setupShortcuts();
}

SearchWidget::~SearchWidget() {
    // Clean up watchers
    if (m_searchWatcher) delete m_searchWatcher;
    if (m_docsWatcher) delete m_docsWatcher;
    if (m_openWatcher) delete m_openWatcher;
}

void SearchWidget::setupUI() {
    QVBoxLayout* mainLayout = new QVBoxLayout(this);
    mainLayout->setSpacing(10);
    mainLayout->setContentsMargins(10, 10, 10, 10);
    
    // Search controls group
    QGroupBox* searchGroup = new QGroupBox("Search", this);
    QGridLayout* searchLayout = new QGridLayout(searchGroup);
    
    // Query input
    m_searchInput = new QLineEdit(this);
    m_searchInput->setPlaceholderText("Enter search query...");
    m_searchInput->setClearButtonEnabled(true);
    
    m_searchButton = new QPushButton("&Search", this);
    m_searchButton->setShortcut(QKeySequence::Find);
    
    searchLayout->addWidget(new QLabel("Query:"), 0, 0);
    searchLayout->addWidget(m_searchInput, 0, 1);
    searchLayout->addWidget(m_searchButton, 0, 2);
    
    // Options row
    m_topKSpin = new QSpinBox(this);
    m_topKSpin->setRange(1, 100);
    m_topKSpin->setValue(10);
    m_topKSpin->setPrefix("Max results: ");
    
    m_liveSearchCheck = new QCheckBox("Live search", this);
    m_liveSearchCheck->setChecked(false);
    m_liveSearchCheck->setToolTip("Search as you type (with delay)");
    
    m_searchModeCombo = new QComboBox(this);
    m_searchModeCombo->addItem("Semantic", "semantic");
    m_searchModeCombo->addItem("Keyword", "keyword");
    m_searchModeCombo->addItem("Hybrid", "hybrid");
    
    searchLayout->addWidget(m_topKSpin, 1, 0);
    searchLayout->addWidget(m_searchModeCombo, 1, 1);
    searchLayout->addWidget(m_liveSearchCheck, 1, 2);
    
    mainLayout->addWidget(searchGroup);
    
    // Filter controls
    QHBoxLayout* filterLayout = new QHBoxLayout;
    m_filterInput = new QLineEdit(this);
    m_filterInput->setPlaceholderText("Filter results...");
    m_filterInput->setClearButtonEnabled(true);
    
    m_sortCombo = new QComboBox(this);
    m_sortCombo->addItem("Sort by Relevance", "score");
    m_sortCombo->addItem("Sort by Date", "date");
    m_sortCombo->addItem("Sort by Path", "path");
    
    m_sortDescendingCheck = new QCheckBox("Descending", this);
    m_sortDescendingCheck->setChecked(true);
    
    filterLayout->addWidget(new QLabel("Filter:"));
    filterLayout->addWidget(m_filterInput);
    filterLayout->addWidget(m_sortCombo);
    filterLayout->addWidget(m_sortDescendingCheck);
    
    mainLayout->addLayout(filterLayout);
    
    // Splitter for results and preview
    m_splitter = new QSplitter(Qt::Horizontal, this);
    
    // Results list
    QWidget* resultsContainer = new QWidget(this);
    QVBoxLayout* resultsLayout = new QVBoxLayout(resultsContainer);
    resultsLayout->setContentsMargins(0, 0, 0, 0);
    
    m_resultsModel = new SearchResultsModel(this);
    m_filterModel = new QSortFilterProxyModel(this);
    m_filterModel->setSourceModel(m_resultsModel);
    m_filterModel->setFilterCaseSensitivity(Qt::CaseInsensitive);
    m_filterModel->setFilterRole(SearchResultsModel::FullTextRole);
    m_filterModel->setSortRole(SearchResultsModel::ScoreRole);
    m_filterModel->setDynamicSortFilter(true);
    
    m_resultsView = new QListView(this);
    m_resultsView->setModel(m_filterModel);
    m_delegate = new SearchResultDelegate(this);
    m_resultsView->setItemDelegate(m_delegate);
    m_resultsView->setSelectionMode(QAbstractItemView::ExtendedSelection);
    m_resultsView->setAlternatingRowColors(true);
    m_resultsView->setSpacing(2);
    
    m_statusLabel = new QLabel("Ready", this);
    m_progressBar = new QProgressBar(this);
    m_progressBar->setRange(0, 0);
    m_progressBar->setVisible(false);
    m_progressBar->setMaximumHeight(4);
    m_progressBar->setTextVisible(false);
    
    resultsLayout->addWidget(m_resultsView);
    resultsLayout->addWidget(m_progressBar);
    resultsLayout->addWidget(m_statusLabel);
    
    m_splitter->addWidget(resultsContainer);
    
    // Preview pane
    m_previewContainer = new QWidget(this);
    QVBoxLayout* previewLayout = new QVBoxLayout(m_previewContainer);
    previewLayout->setContentsMargins(0, 0, 0, 0);
    
    m_previewMetaLabel = new QLabel(this);
    m_previewMetaLabel->setWordWrap(true);
    m_previewMetaLabel->setStyleSheet("QLabel { background-color: palette(alternate-base); padding: 5px; }");
    
    m_previewEdit = new QTextEdit(this);
    m_previewEdit->setReadOnly(true);
    m_previewEdit->setLineWrapMode(QTextEdit::WidgetWidth);
    m_highlighter = new SearchHighlighter(m_previewEdit->document());
    
    QHBoxLayout* previewBtnLayout = new QHBoxLayout;
    m_openButton = new QPushButton("&Open", this);
    m_copyButton = new QPushButton("&Copy", this);
    previewBtnLayout->addStretch();
    previewBtnLayout->addWidget(m_openButton);
    previewBtnLayout->addWidget(m_copyButton);
    
    previewLayout->addWidget(m_previewMetaLabel);
    previewLayout->addWidget(m_previewEdit);
    previewLayout->addLayout(previewBtnLayout);
    
    m_splitter->addWidget(m_previewContainer);
    m_splitter->setSizes({400, 600});
    
    mainLayout->addWidget(m_splitter, 1);
    
    // Context menu
    m_contextMenu = new QMenu(this);
    m_openAction = m_contextMenu->addAction("&Open Document", this, &SearchWidget::openSelectedDocument);
    m_contextMenu->addSeparator();
    m_copyTextAction = m_contextMenu->addAction("Copy &Text", this, &SearchWidget::copySelectedToClipboard);
    m_copyPathAction = m_contextMenu->addAction("Copy &Path", this, [this]() {
        if (!hasSelection()) return;
        auto result = getSelectedResult();
        QApplication::clipboard()->setText(result.document.sourcePath);
    });
    m_contextMenu->addSeparator();
    m_showInFolderAction = m_contextMenu->addAction("Show in &Folder", this, [this]() {
        if (!hasSelection()) return;
        auto result = getSelectedResult();
        QFileInfo info(result.document.sourcePath);
        QDesktopServices::openUrl(QUrl::fromLocalFile(info.dir().absolutePath()));
    });
    m_exportAction = m_contextMenu->addAction("&Export Results...", this, &SearchWidget::exportResults);
}

void SearchWidget::setupConnections() {
    // Search triggers
    connect(m_searchButton, &QPushButton::clicked, this, &SearchWidget::onSearchTriggered);
    connect(m_searchInput, &QLineEdit::returnPressed, this, &SearchWidget::onSearchTriggered);
    connect(m_searchInput, &QLineEdit::textChanged, this, &SearchWidget::onSearchTextChanged);
    
    // Live search timer
    m_liveSearchTimer->setSingleShot(true);
    connect(m_liveSearchTimer, &QTimer::timeout, this, [this]() {
        if (m_liveSearchCheck->isChecked() && !m_searchInput->text().isEmpty()) {
            performSearch(m_searchInput->text());
        }
    });
    
    // Result selection
    connect(m_resultsView->selectionModel(), &QItemSelectionModel::selectionChanged,
            this, &SearchWidget::onSelectionChanged);
    connect(m_resultsView, &QListView::clicked, this, &SearchWidget::onResultClicked);
    connect(m_resultsView, &QListView::doubleClicked, this, &SearchWidget::onResultDoubleClicked);
    
    // Filtering and sorting
    connect(m_filterInput, &QLineEdit::textChanged, this, &SearchWidget::onFilterTextChanged);
    connect(m_sortCombo, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, &SearchWidget::onSortOrderChanged);
    connect(m_sortDescendingCheck, &QCheckBox::stateChanged, this, &SearchWidget::onSortOrderChanged);
    
    // Buttons
    connect(m_openButton, &QPushButton::clicked, this, &SearchWidget::openSelectedDocument);
    connect(m_copyButton, &QPushButton::clicked, this, &SearchWidget::copySelectedToClipboard);
    
    // Context menu
    m_resultsView->setContextMenuPolicy(Qt::CustomContextMenu);
    connect(m_resultsView, &QListView::customContextMenuRequested,
            this, &SearchWidget::showResultContextMenu);
}

void SearchWidget::setupShortcuts() {
    // FIX: Qt6 removed the 4-argument QShortcut(key, parent, receiver, slot) constructor.
    //      Use the 3-argument functor form: QShortcut(key, parent, functor) instead.
    connect(new QShortcut(QKeySequence::FindNext, this), &QShortcut::activated,
            this, &SearchWidget::selectNextResult);
    connect(new QShortcut(QKeySequence::FindPrevious, this), &QShortcut::activated,
            this, &SearchWidget::selectPreviousResult);
    connect(new QShortcut(QKeySequence("Ctrl+O"), this), &QShortcut::activated,
            this, &SearchWidget::openSelectedDocument);
    connect(new QShortcut(QKeySequence("Ctrl+C"), this), &QShortcut::activated,
            this, &SearchWidget::copySelectedToClipboard);
    connect(new QShortcut(QKeySequence("Ctrl+R"), this), &QShortcut::activated,
            this, &SearchWidget::refreshCurrentSearch);
    connect(new QShortcut(QKeySequence("Esc"), this), &QShortcut::activated, this, [this]() {
        if (m_isSearching) {
            // Cancel search if implemented
        } else {
            clearSearch();
        }
    });
}

void SearchWidget::performSearch(const QString& query) {
    QString searchQuery = query.isEmpty() ? m_searchInput->text() : query;
    if (searchQuery.isEmpty()) return;
    
    m_currentQuery = searchQuery;
    m_isSearching = true;
    m_searchButton->setEnabled(false);
    m_progressBar->setVisible(true);
    m_statusLabel->setText("Searching...");
    m_resultsModel->clearResults();
    m_previewEdit->clear();
    m_previewMetaLabel->clear();
    
    emit searchStarted(searchQuery);
    
    // Parse search query for highlighting
    QStringList terms = searchQuery.split(QRegularExpression("\\s+"), Qt::SkipEmptyParts);
    m_highlighter->setSearchTerms(terms);
    
    // Execute async search
    auto future = m_apiClient->search(searchQuery, m_topKSpin->value());
    
    m_searchWatcher = new QFutureWatcher<QList<SearchResult>>(this);
    connect(m_searchWatcher, &QFutureWatcher<QList<SearchResult>>::finished,
            this, &SearchWidget::onSearchFinished);
    m_searchWatcher->setFuture(future);
}

void SearchWidget::onSearchFinished() {
    try {
        m_currentResults = m_searchWatcher->result();
        
        if (m_currentResults.isEmpty()) {
            m_statusLabel->setText("No results found");
            emit searchCompleted(0);
            cleanupSearch();
            return;
        }
        
        // Fetch full document details
        QList<QUuid> ids;
        for (const auto& r : m_currentResults) {
            ids.append(r.document.documentPartId);
        }
        
        auto docFuture = m_apiClient->batchGetDocuments(ids);
        m_docsWatcher = new QFutureWatcher<QList<DocumentPart>>(this);
        connect(m_docsWatcher, &QFutureWatcher<QList<DocumentPart>>::finished,
                this, &SearchWidget::onDocumentsFetched);
        m_docsWatcher->setFuture(docFuture);
        
    } catch (const std::exception& e) {
        m_statusLabel->setText(QString("Error: %1").arg(e.what()));
        emit searchError(e.what());
        cleanupSearch();
    }
    
    m_searchWatcher->deleteLater();
    m_searchWatcher = nullptr;
}

void SearchWidget::onDocumentsFetched() {
    try {
        auto docs = m_docsWatcher->result();
        
        // Update results with full document data
        for (int i = 0; i < docs.size() && i < m_currentResults.size(); ++i) {
            m_currentResults[i].document = docs[i];
        }
        
        m_resultsModel->setResults(m_currentResults);
        m_filterModel->invalidate();
        
        // Auto-sort by score descending
        m_filterModel->sort(0, Qt::DescendingOrder);
        
        m_statusLabel->setText(QString("Found %1 results").arg(m_currentResults.size()));
        emit searchCompleted(m_currentResults.size());
        
    } catch (const std::exception& e) {
        m_statusLabel->setText(QString("Error fetching documents: %1").arg(e.what()));
        emit searchError(e.what());
    }
    
    cleanupSearch();
    m_docsWatcher->deleteLater();
    m_docsWatcher = nullptr;
}

void SearchWidget::cleanupSearch() {
    m_isSearching = false;
    m_searchButton->setEnabled(true);
    m_progressBar->setVisible(false);
}

void SearchWidget::onSelectionChanged(const QItemSelection& selected, const QItemSelection& deselected) {
    QModelIndexList indexes = selected.indexes();
    if (indexes.isEmpty()) return;
    
    int sourceRow = m_filterModel->mapToSource(indexes.first()).row();
    if (sourceRow >= 0 && sourceRow < m_currentResults.size()) {
        updatePreview(m_currentResults[sourceRow]);
        emit resultSelected(m_currentResults[sourceRow]);
    }
}

void SearchWidget::updatePreview(const SearchResult& result) {
    const DocumentPart& doc = result.document;
    
    // Update metadata label
    m_previewMetaLabel->setText(
        QString("<b>%1</b><br>"
                "<small>Score: %2 | Type: %3 | Created: %4 | ID: %5</small>")
        .arg(doc.sourcePath.toHtmlEscaped())
        .arg(result.score, 0, 'f', 4)
        .arg(doc.contentType.toHtmlEscaped())
        .arg(doc.createdAt.toString())
        .arg(doc.documentPartId.toString())
    );
    
    // Update text preview with highlighting
    QString previewText = doc.text;
    if (previewText.length() > 10000) {
        previewText = previewText.left(10000) + "\n\n[... Content truncated ...]";
    }
    m_previewEdit->setPlainText(previewText);
    
    // Scroll to first match
    if (!m_currentQuery.isEmpty()) {
        QString firstTerm = m_currentQuery.split(QRegularExpression("\\s+")).first();
        QTextDocument* document = m_previewEdit->document();
        QTextCursor cursor = document->find(firstTerm);
        if (!cursor.isNull()) {
            m_previewEdit->setTextCursor(cursor);
            m_previewEdit->ensureCursorVisible();
        }
    }
}

void SearchWidget::openSelectedDocument() {
    if (!hasSelection()) return;
    
    auto result = getSelectedResult();
    emit documentOpened(result);
    
    auto future = m_apiClient->getOpenDescriptor(result.document.documentPartId);
    m_openWatcher = new QFutureWatcher<QJsonObject>(this);
    connect(m_openWatcher, &QFutureWatcher<QJsonObject>::finished,
            this, &SearchWidget::onOpenDescriptorReceived);
    m_openWatcher->setFuture(future);
}

void SearchWidget::onOpenDescriptorReceived() {
    try {
        QJsonObject desc = m_openWatcher->result();
        QString sourceType = desc["source_type"].toString();
        QString target = desc["target"].toString();
        
        if (sourceType == "filesystem" || sourceType == "url") {
            QDesktopServices::openUrl(QUrl::fromLocalFile(target));
        } else if (sourceType == "thunderbird") {
            QRegularExpression re("<(.*?)>");
            QRegularExpressionMatch match = re.match(target);
            if (match.hasMatch()) {
                QString messageId = match.captured(1);
                QProcess::startDetached("thunderbird", QStringList() << QString("mid:%1").arg(messageId));
            }
        }
    } catch (const std::exception& e) {
        QMessageBox::critical(this, "Error", QString("Failed to open document: %1").arg(e.what()));
    }
    
    m_openWatcher->deleteLater();
    m_openWatcher = nullptr;
}

void SearchWidget::copySelectedToClipboard() {
    if (!hasSelection()) return;
    
    auto result = getSelectedResult();
    QString text = QString("Source: %1\nScore: %2\n\n%3")
        .arg(result.document.sourcePath)
        .arg(result.score)
        .arg(result.document.text.left(5000));
    
    QApplication::clipboard()->setText(text);
    // FIX: QLabel::setText() takes only one argument. The second argument (timeout)
    //      is for QStatusBar::showMessage(), not QLabel. Use setText() alone.
    m_statusLabel->setText("Copied to clipboard");
}

void SearchWidget::exportResults() {
    QString fileName = QFileDialog::getSaveFileName(this, "Export Results", 
                                                   "search_results.json", 
                                                   "JSON (*.json);;CSV (*.csv)");
    if (fileName.isEmpty()) return;
    
    // Implementation for exporting results to file
    // Would write m_currentResults to JSON or CSV format
}

void SearchWidget::clearSearch() {
    m_searchInput->clear();
    m_filterInput->clear();
    m_resultsModel->clearResults();
    m_currentResults.clear();
    m_previewEdit->clear();
    m_previewMetaLabel->clear();
    m_statusLabel->setText("Ready");
    m_highlighter->clearHighlight();
}

void SearchWidget::refreshCurrentSearch() {
    if (!m_currentQuery.isEmpty()) {
        performSearch(m_currentQuery);
    }
}

void SearchWidget::focusSearch() {
    m_searchInput->setFocus();
    m_searchInput->selectAll();
}

void SearchWidget::selectNextResult() {
    int current = m_resultsView->currentIndex().row();
    int next = (current + 1) % m_filterModel->rowCount();
    m_resultsView->setCurrentIndex(m_filterModel->index(next, 0));
}

void SearchWidget::selectPreviousResult() {
    int current = m_resultsView->currentIndex().row();
    int prev = (current - 1 + m_filterModel->rowCount()) % m_filterModel->rowCount();
    m_resultsView->setCurrentIndex(m_filterModel->index(prev, 0));
}

void SearchWidget::onSearchTextChanged(const QString& text) {
    if (m_liveSearchCheck->isChecked()) {
        m_liveSearchTimer->stop();
        m_liveSearchTimer->start(m_liveSearchDelayMs);
    }
}

void SearchWidget::onFilterTextChanged(const QString& text) {
    m_filterModel->setFilterFixedString(text);
    m_statusLabel->setText(QString("Showing %1 of %2 results")
        .arg(m_filterModel->rowCount())
        .arg(m_currentResults.size()));
}

void SearchWidget::onSortOrderChanged(int) {
    Qt::SortOrder order = m_sortDescendingCheck->isChecked() ? Qt::DescendingOrder : Qt::AscendingOrder;
    int role = SearchResultsModel::ScoreRole;
    
    QString sortType = m_sortCombo->currentData().toString();
    if (sortType == "date") role = Qt::UserRole + 11;  // created_at
    else if (sortType == "path") role = Qt::ToolTipRole;  // source_path
    
    m_filterModel->setSortRole(role);
    m_filterModel->sort(0, order);
}

void SearchWidget::showResultContextMenu(const QPoint& pos) {
    QModelIndex index = m_resultsView->indexAt(pos);
    if (!index.isValid()) return;
    
    m_resultsView->setCurrentIndex(index);
    m_contextMenu->exec(m_resultsView->mapToGlobal(pos));
}

void SearchWidget::setApiClient(ApiClient* client) {
    m_apiClient = client;
}

void SearchWidget::setDefaultTopK(int topK) {
    m_topKSpin->setValue(topK);
}

QList<SearchResult> SearchWidget::getCurrentResults() const {
    return m_currentResults;
}

SearchResult SearchWidget::getSelectedResult() const {
    QModelIndexList selected = m_resultsView->selectionModel()->selectedIndexes();
    if (selected.isEmpty()) return SearchResult();
    
    int sourceRow = m_filterModel->mapToSource(selected.first()).row();
    return m_resultsModel->getResultAt(sourceRow);
}

bool SearchWidget::hasSelection() const {
    return !m_resultsView->selectionModel()->selectedIndexes().isEmpty();
}

void SearchWidget::keyPressEvent(QKeyEvent* event) {
    if (event->key() == Qt::Key_Escape) {
        if (m_isSearching) {
            // Could cancel future here if supported
        } else {
            clearSearch();
        }
    }
    QWidget::keyPressEvent(event);
}

// Stub implementations for slots declared in header but not shown in original
void SearchWidget::onResultClicked(const QModelIndex& index) {
    // Selection change is handled via selectionModel signal
}

void SearchWidget::onResultDoubleClicked(const QModelIndex& index) {
    int sourceRow = m_filterModel->mapToSource(index).row();
    if (sourceRow >= 0 && sourceRow < m_currentResults.size()) {
        emit resultActivated(m_currentResults[sourceRow]);
        openSelectedDocument();
    }
}

void SearchWidget::onSearchTriggered() {
    performSearch(m_searchInput->text());
}

void SearchWidget::togglePreviewPane(bool visible) {
    m_previewContainer->setVisible(visible);
}

void SearchWidget::toggleLiveSearch(bool enabled) {
    if (!enabled) m_liveSearchTimer->stop();
}

void SearchWidget::contextMenuEvent(QContextMenuEvent* event) {
    m_contextMenu->exec(event->globalPos());
}
