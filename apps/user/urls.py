from django.urls import path, re_path
from django.contrib.auth.decorators import login_required
from user.views import RegisterView, ActiveView, LoginView, UserInfoView, UserOrderView, UserAddressView, LogoutView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    re_path('active/(?P<token>.*)$', ActiveView.as_view(), name='active'),

    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # path('', login_required(UserInfoView.as_view()), name='user'),
    # path('order/', login_required(UserOrderView.as_view()), name='order'),
    path('', UserInfoView.as_view(), name='user'),
    path('order/', UserOrderView.as_view(), name='order'),
    path('address/', UserAddressView.as_view(), name='address'),
]
