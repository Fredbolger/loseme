#ifndef RUNSCONTROLLER_H
#define RUNSCONTROLLER_H

#include <QWidget>
#include <QTableWidget>
#include <QPushButton>
#include <QCheckBox>      // FIX: was missing — QCheckBox used as m_autoRefreshCheck
#include <QTimer>
#include <QInputDialog>   // FIX: was missing — QInputDialog::getText used in stopLatest/resumeLatest
#include <QApplication>   // FIX: was missing — QApplication::clipboard() used in context menu
#include "apiclient.h"

class RunsController : public QWidget {
    Q_OBJECT

public:
    explicit RunsController(ApiClient* client, QWidget* parent = nullptr);

private slots:
    void refreshRuns();
    void stopSelected();
    void stopLatest();
    void resumeLatest();
    void autoRefresh();
    
private:
    void setupUI();
    void updateTable(const QList<IndexingRun>& runs);
    
    ApiClient* m_apiClient;
    QTableWidget* m_table;
    QPushButton* m_refreshBtn;
    QPushButton* m_stopBtn;
    QPushButton* m_stopLatestBtn;
    QPushButton* m_resumeBtn;
    QCheckBox* m_autoRefreshCheck;
    QTimer* m_refreshTimer;
};

#endif // RUNSCONTROLLER_H
