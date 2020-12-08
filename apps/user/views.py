from django.shortcuts import render, redirect, HttpResponse
from django.urls import reverse
from django.views.generic import View
from django.core.mail import send_mail
from django.contrib.auth import authenticate, login, logout
from django_redis import get_redis_connection

from itsdangerous import TimedJSONWebSignatureSerializer, SignatureExpired

from df import settings
from user.models import User, Address, AddressManage
from goods.models import GoodsSKU
from utils.mixin import LoginRequiredMixin

import re
import json

# Create your views here.
class RegisterView(View):
    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        if not all([username, password, email]):
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式有误'})

        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '未勾选协议'})

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None

        if user:
            return render(request, 'register.html', {'errmsg': '用户名已存在'})

        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()

        user_info = {
            'user_id': user.id,
        }
        token = TimedJSONWebSignatureSerializer(secret_key=settings.SECRET_KEY, expires_in=30)
        token = token.dumps(user_info)
        token = token.decode()

        # 发邮件
        subject = '淘生鲜欢迎您'
        message = ''
        sender = settings.EMAIL_FROM
        receiver = [email]
        html_message = f'<h1>{username}您好，欢迎您成为淘生鲜注册用户</h1>请点击以下链接激活您的账号<a href="http://127.0.0.1:8000/user/active/{token}">http://127.0.0.1:8000/user/active/{token}</a>'
        # 发送激活邮件
        send_mail(subject, message, sender, receiver, html_message=html_message)

        return redirect(reverse('goods:index'))

class ActiveView(View):
    def get(self, request, token):
        recv_token = TimedJSONWebSignatureSerializer(secret_key=settings.SECRET_KEY, expires_in=30)

        try:
            user_info = recv_token.loads(token)

            user = User.objects.get(id=user_info['user_id'])
            user.is_active = 1
            user.save()

            return redirect(reverse('user:login'))

        except SignatureExpired:
            return HttpResponse('激活链接已过期')


class LoginView(View):
    def get(self, request):
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            print(type(username))
            username = json.loads(username)
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request, 'login.html', {'username':username, 'checked':checked})

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('pwd')

        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '数据不完整'})

        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)

                next_url = request.GET.get('next', reverse('goods:index'))
                res = redirect(next_url)  # HttpResponseRedirect

                remember = request.POST.get('remember')
                if remember == 'on':
                    username_json = json.dumps(username)
                    res.set_cookie('username', username_json, max_age=24*3600)
                else:
                    res.delete_cookie('username')
                return res
            else:
                return render(request, 'login.html', {'errmsg': '用户未激活'})
        else:
            return render(request, 'login.html', {'errmsg': '用户名或密码不正确'})

class LogoutView(LoginRequiredMixin, View):
    def get(self, request):
        logout(request)
        return redirect(reverse('goods:index'))

class UserInfoView(LoginRequiredMixin, View):
    def get(self, request):
        page = 'user'
        user = request.user
        address = Address.objects.get_default_address(user=user)
        # 方法一(拿到与Redis数据库的链接)
        # from redis import StrictRedis
        # sr = StrictRedis(host='127.0.0.1:6379', port='6379', db=1)
        # 方法二
        con = get_redis_connection('default')
        history_key = f'history_{user.id}'
        # 获取最近5条历史浏览记录
        sku_ids = con.lrange(history_key, 0, 4)
        # 获取方法1
        # goods_res = GoodsSKU.objects.filter(goods_id__in=sku_ids)
        # goods_li = []
        # for id in sku_ids:
        #     for goods in goods_res:
        #         if id == goods.id:
        #             goods_li.append(goods)
        # 获取方法2
        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)

        # 组织上下文
        context = {'page': page,
                   'address': address,
                   'goods_li': goods_li}

        return render(request, 'user_center_info.html', context)

class UserOrderView(LoginRequiredMixin, View):
    def get(self, request):
        page = 'order'
        return render(request, 'user_center_order.html', {'page': page})


class UserAddressView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        address = Address.objects.get_default_address(user)
        page = 'address'
        return render(request, 'user_center_site.html', {'page': page, 'address': address})
    def post(self, request):
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'errmsg': '数据不完整',})
        if not re.match(r'1[3,4,5,7,8]\d{9}$', phone):
            return render(request, 'user_center_site.html', {'errmsg': '手机号格式有误'})
        if len(zip_code) != 6:
            return render(request, 'user_center_site.html', {'errmsg': '邮件编码错误'})
        user = request.user
        address = Address.objects.get_default_address(user)
        if address:
            is_default = False
        else:
            is_default = True
        Address.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default)
        return redirect(reverse('user:address'))

