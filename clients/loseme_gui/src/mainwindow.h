#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QTabWidget>
#include <QStatusBar>
#include <QProgressBar>
#include <QLineEdit>
#include <QPushButton>
#include <QListWidget>
#include <QTextEdit>
#include <QSplitter>
#include <QTreeWidget>
#include <QSpinBox>    // FIX: was missing — QSpinBox used in mainwindow.cpp
#include <QCheckBox>   // FIX: was missing — QCheckBox used in mainwindow.cpp
#include <QProcess>    // FIX: was missing — QProcess::startDetached used in mainwindow.cpp
#include "apiclient.h"
#include "ingestdialog.h"
#include "sourceswidget.h"
#include "runscontroller.h"

class MainWindow : public QMainWindow {
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    void performSearch();
    void onSearchResultClicked(QListWidgetItem* item);
    void showIngestDialog();
    void showSourcesManager();
    void showRunsManager();
    void openSelectedDocument();
    void updateStatus(const QString& message);

private:
    void setupUI();
    void setupSearchTab();
    void setupConnections();
    
    ApiClient* m_apiClient;
    
    // UI Elements
    QTabWidget* m_tabWidget;
    
    // Search tab
    QWidget* m_searchTab;
    QLineEdit* m_searchInput;
    QPushButton* m_searchButton;
    QSpinBox* m_topKSpin;
    QListWidget* m_resultsList;
    QTextEdit* m_previewPane;
    QCheckBox* m_interactiveCheck;
    
    // Menu actions
    QAction* m_ingestAction;
    QAction* m_sourcesAction;
    QAction* m_runsAction;
    
    // Dialogs — FIX: initialize to nullptr so null-checks in show*() methods are safe
    IngestDialog* m_ingestDialog = nullptr;
    SourcesWidget* m_sourcesWidget = nullptr;
    RunsController* m_runsController = nullptr;
    
    // Current search results cache
    QList<SearchResult> m_currentResults;
};

#endif // MAINWINDOW_H
