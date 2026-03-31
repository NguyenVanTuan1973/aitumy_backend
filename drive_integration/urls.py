from django.urls import path
from .views import DriveStatusView, DriveConnectView, DriveOAuthCallbackView, DriveDisconnectView, \
    DriveAuthUrlView, DriveInitFolderView, GetDataSheetAPIView, CreateDocumentAPIView

urlpatterns = [
    # ======================
    # OAuth
    # ======================
    path("auth-url/", DriveAuthUrlView.as_view(), name= 'auth-url'),
    path('oauth/callback/', DriveOAuthCallbackView.as_view(), name= 'oauth-callback'),
    path('connect/', DriveConnectView.as_view(), name= 'connect'),
    path('disconnect/', DriveDisconnectView.as_view(), name= 'disconnect'),

    # ======================
    # Workspace
    # ======================
    path('status/', DriveStatusView.as_view(), name= 'status'),
    path('init-workspace/', DriveInitFolderView.as_view(), name= 'init-workspace'),

    # ======================
    # Sheet
    # ======================
    path("sheet/append/", CreateDocumentAPIView.as_view(), name= 'sheet-append'),
    path("sheet/data/", GetDataSheetAPIView.as_view(), name= 'sheet-data'),     # cũ /api/drive/get-data-sheet-view/

]
