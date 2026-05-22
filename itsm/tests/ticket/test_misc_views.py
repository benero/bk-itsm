# -*- coding: utf-8 -*-
"""
spec round3 H-D / H-E / M-A 鉴权回归。

``CommentInviteViewSet`` 等 viewset 当前未在 ``itsm/ticket/urls.py`` 中注册路由，
因此用类级单元测试覆盖：
- queryset 必须按归属过滤；
- ITSM 超管短路；
- ``http_method_names`` 仅暴露只读；
- 显式 ``permission_classes`` 含 ``IsAuthenticated``。
"""

from unittest.mock import patch, MagicMock

from django.test import TestCase
from rest_framework.permissions import IsAuthenticated

from itsm.ticket.models import (
    Ticket,
    TicketComment,
    TicketCommentInvite,
)
from itsm.ticket.views.misc import (
    CommentInviteViewSet,
    StateDraftViewSet,
    TemplateViewSet,
)


def _fake_request(username):
    request = MagicMock()
    request.user.username = username
    return request


class CommentInviteViewSetAuthzTest(TestCase):
    """spec round3 H-D。"""

    def setUp(self):
        Ticket.objects.all().delete()
        TicketComment.objects.all().delete()
        TicketCommentInvite.objects.all().delete()

        self.alice_ticket = Ticket.objects.create(
            sn="SN-ALICE", title="t1", service_id=1, service_type="request",
            creator="alice", current_status="RUNNING", project_key="public",
        )
        self.bob_ticket = Ticket.objects.create(
            sn="SN-BOB", title="t2", service_id=1, service_type="request",
            creator="bob", current_status="RUNNING", project_key="public",
        )

        self.alice_comment = TicketComment.objects.create(
            ticket=self.alice_ticket, creator="alice"
        )
        self.bob_comment = TicketComment.objects.create(
            ticket=self.bob_ticket, creator="bob"
        )

        self.alice_invite = TicketCommentInvite.objects.create(
            comment=self.alice_comment, code="ALICE01", receiver="alice@x"
        )
        self.bob_invite = TicketCommentInvite.objects.create(
            comment=self.bob_comment, code="BOBCD02", receiver="bob@x"
        )

    def _make_viewset(self, username):
        viewset = CommentInviteViewSet()
        viewset.request = _fake_request(username)
        return viewset

    def test_permission_classes_contains_is_authenticated(self):
        self.assertIn(IsAuthenticated, CommentInviteViewSet.permission_classes)

    def test_http_method_names_is_readonly(self):
        # 任意写动作（POST/PUT/PATCH/DELETE）必须被 405 拦截
        self.assertEqual(
            sorted(CommentInviteViewSet.http_method_names),
            sorted(["get", "head", "options"]),
        )

    @patch("itsm.ticket.views.misc.UserRole.is_itsm_superuser", return_value=False)
    def test_get_queryset_filters_by_comment_creator(self, _superuser):
        viewset = self._make_viewset("alice")
        ids = list(viewset.get_queryset().values_list("id", flat=True))
        self.assertEqual(ids, [self.alice_invite.id])

    @patch("itsm.ticket.views.misc.UserRole.is_itsm_superuser", return_value=False)
    def test_get_queryset_excludes_others_for_non_owner(self, _superuser):
        viewset = self._make_viewset("carol")
        self.assertEqual(viewset.get_queryset().count(), 0)

    @patch("itsm.ticket.views.misc.UserRole.is_itsm_superuser", return_value=True)
    def test_get_queryset_short_circuits_for_superuser(self, _superuser):
        viewset = self._make_viewset("admin")
        ids = set(viewset.get_queryset().values_list("id", flat=True))
        self.assertEqual(ids, {self.alice_invite.id, self.bob_invite.id})


class TemplateViewSetAuthzTest(TestCase):
    """spec round3 H-E：显式 IsAuthenticated。"""

    def test_permission_classes_contains_is_authenticated(self):
        self.assertIn(IsAuthenticated, TemplateViewSet.permission_classes)


class StateDraftViewSetAuthzTest(TestCase):
    """spec round3 M-A：显式 IsAuthenticated。"""

    def test_permission_classes_contains_is_authenticated(self):
        self.assertIn(IsAuthenticated, StateDraftViewSet.permission_classes)
