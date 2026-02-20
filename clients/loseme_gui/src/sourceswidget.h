#ifndef SOURCESWIDGET_H
#define SOURCESWIDGET_H

#include <QWidget>
#include <QTreeWidget>
#include <QPushButton>
#include <QComboBox>
#include <QLineEdit>
#include <QCheckBox>
#include <QListWidget>
#include <QDialog>
#include <QStackedWidget>
#include <QInputDialog>
#include <QFileDialog>
#include <QMessageBox>
#include <QFutureWatcher>
#include "apiclient.h"
#include "models/indexingscope.h"

/**
 * Dialog for adding new sources (Filesystem or Thunderbird)
 */
class AddSourceDialog : public QDialog {
    Q_OBJECT

public:
    explicit AddSourceDialog(ApiClient* client, QWidget* parent = nullptr);
    
    QString getSourceType() const;
    QString getScopeJson() const;

private slots:
    void onTypeChanged(int index);
    void browsePath();
    void validateAndAccept();

private:
    void setupUI();
    
    ApiClient* m_apiClient;
    
    QComboBox* m_typeCombo;
    QStackedWidget* m_stack;
    
    // Filesystem widgets
    QLineEdit* m_fsPath;
    QCheckBox* m_fsRecursive;
    QListWidget* m_fsIncludeList;
    QListWidget* m_fsExcludeList;
    
    // Thunderbird widgets
    QLineEdit* m_tbPath;
    QListWidget* m_tbIgnoreList;
};

/**
 * Widget for managing monitored sources with scan capability
 */
class SourcesWidget : public QWidget {
    Q_OBJECT

public:
    explicit SourcesWidget(ApiClient* client, QWidget* parent = nullptr);

private slots:
    void refreshSources();
    void addSource();
    void scanSource();
    void toggleSource();
    void deleteSource();
    void onSourceDoubleClicked(QTreeWidgetItem* item, int column);
    
private:
    void setupUI();
    void populateTree(const QJsonArray& sources);
    QJsonObject getSourceAt(int index) const;
    
    ApiClient* m_apiClient;
    
    QTreeWidget* m_tree;
    QPushButton* m_refreshBtn;
    QPushButton* m_addBtn;
    QPushButton* m_scanBtn;
    QPushButton* m_toggleBtn;
    QPushButton* m_deleteBtn;
    
    QJsonArray m_currentSources;
};

#endif // SOURCESWIDGET_H
