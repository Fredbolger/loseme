#ifndef SEARCHWIDGET_H
#define SEARCHWIDGET_H

#include <QWidget>
#include <QLineEdit>
#include <QPushButton>
#include <QSpinBox>
#include <QListView>
#include <QTextEdit>
#include <QSplitter>
#include <QCheckBox>
#include <QComboBox>
#include <QProgressBar>
#include <QLabel>
#include <QSortFilterProxyModel>
#include <QStandardItemModel>
#include <QTimer>
#include <QMenu>
#include <QAction>
#include <QKeySequence>
#include <QShortcut>
#include "apiclient.h"
#include "models/documentpart.h"

// Forward declarations
class SearchResultDelegate;
class SearchHighlighter;

/**
 * Custom model for search results with rich data storage
 */
class SearchResultsModel : public QStandardItemModel {
    Q_OBJECT

public:
    explicit SearchResultsModel(QObject* parent = nullptr);
    
    void setResults(const QList<SearchResult>& results);
    QList<SearchResult> getResults() const;
    SearchResult getResultAt(int index) const;
    void clearResults();
    
    // Custom roles for data retrieval
    static constexpr int DocumentPartRole = Qt::UserRole + 1;
    static constexpr int ScoreRole = Qt::UserRole + 2;
    static constexpr int FullTextRole = Qt::UserRole + 3;

private:
    QList<SearchResult> m_results;
};

/**
 * Delegate for rendering search results with score indicators and icons
 */
class SearchResultDelegate : public QStyledItemDelegate {
    Q_OBJECT

public:
    explicit SearchResultDelegate(QObject* parent = nullptr);
    
    void paint(QPainter* painter, const QStyleOptionViewItem& option, 
               const QModelIndex& index) const override;
    QSize sizeHint(const QStyleOptionViewItem& option, 
                   const QModelIndex& index) const override;

private:
    QColor scoreToColor(double score) const;
};

/**
 * Syntax highlighter for search term highlighting in preview
 */
class SearchHighlighter : public QSyntaxHighlighter {
    Q_OBJECT

public:
    explicit SearchHighlighter(QTextDocument* parent = nullptr);
    
    void setSearchTerms(const QStringList& terms);
    void clearHighlight();

protected:
    void highlightBlock(const QString& text) override;

private:
    QStringList m_searchTerms;
    QList<QTextCharFormat> m_formats;
};

/**
 * Advanced search widget with real-time search, filtering, and preview
 */
class SearchWidget : public QWidget {
    Q_OBJECT

public:
    explicit SearchWidget(ApiClient* client, QWidget* parent = nullptr);
    ~SearchWidget();

    // Configuration
    void setApiClient(ApiClient* client);
    void setDefaultTopK(int topK);
    
    // Search operations
    void performSearch(const QString& query = QString());
    void clearSearch();
    void refreshCurrentSearch();
    
    // Results access
    QList<SearchResult> getCurrentResults() const;
    SearchResult getSelectedResult() const;
    bool hasSelection() const;

signals:
    // Navigation signals
    void resultSelected(const SearchResult& result);
    void resultActivated(const SearchResult& result);  // Double-click or Enter
    void documentOpened(const SearchResult& result);
    
    // State signals
    void searchStarted(const QString& query);
    void searchCompleted(int resultCount);
    void searchError(const QString& error);
    void searchCancelled();

public slots:
    void focusSearch();
    void selectNextResult();
    void selectPreviousResult();
    void openSelectedDocument();
    void copySelectedToClipboard();

protected:
    void keyPressEvent(QKeyEvent* event) override;
    void contextMenuEvent(QContextMenuEvent* event) override;

private slots:
    void onSearchTriggered();
    void onSearchTextChanged(const QString& text);
    void onResultClicked(const QModelIndex& index);
    void onResultDoubleClicked(const QModelIndex& index);
    void onSelectionChanged(const QItemSelection& selected, const QItemSelection& deselected);
    void onFilterTextChanged(const QString& text);
    void onSortOrderChanged(int index);
    void onSearchFinished();
    void onDocumentsFetched();
    void onOpenDescriptorReceived();
    void showResultContextMenu(const QPoint& pos);
    void togglePreviewPane(bool visible);
    void toggleLiveSearch(bool enabled);
    void exportResults();

private:
    void setupUI();
    void setupConnections();
    void setupShortcuts();
    void updatePreview(const SearchResult& result);
    void highlightSearchTerms(const QString& text);
    QString truncateText(const QString& text, int maxLength) const;
    QString formatResultPreview(const DocumentPart& doc) const;

    // Core components
    ApiClient* m_apiClient;
    SearchResultsModel* m_resultsModel;
    QSortFilterProxyModel* m_filterModel;
    SearchResultDelegate* m_delegate;
    SearchHighlighter* m_highlighter;
    
    // UI Elements - Search Controls
    QLineEdit* m_searchInput;
    QPushButton* m_searchButton;
    QSpinBox* m_topKSpin;
    QCheckBox* m_liveSearchCheck;
    QComboBox* m_searchModeCombo;  // Exact, Fuzzy, Semantic
    
    // UI Elements - Filters
    QLineEdit* m_filterInput;
    QComboBox* m_sortCombo;
    QCheckBox* m_sortDescendingCheck;
    
    // UI Elements - Results
    QListView* m_resultsView;
    QLabel* m_statusLabel;
    QProgressBar* m_progressBar;
    
    // UI Elements - Preview
    QSplitter* m_splitter;
    QWidget* m_previewContainer;
    QTextEdit* m_previewEdit;
    QLabel* m_previewMetaLabel;
    QPushButton* m_openButton;
    QPushButton* m_copyButton;
    
    // Context menu actions
    QMenu* m_contextMenu;
    QAction* m_openAction;
    QAction* m_copyTextAction;
    QAction* m_copyPathAction;
    QAction* m_showInFolderAction;
    QAction* m_exportAction;
    
    // State
    QString m_currentQuery;
    QList<SearchResult> m_currentResults;
    bool m_isSearching;
    QTimer* m_liveSearchTimer;
    int m_liveSearchDelayMs = 300;
    
    // Async operation tracking
    QFutureWatcher<QList<SearchResult>>* m_searchWatcher;
    QFutureWatcher<QList<DocumentPart>>* m_docsWatcher;
    QFutureWatcher<QJsonObject>* m_openWatcher;
};

#endif // SEARCHWIDGET_H
