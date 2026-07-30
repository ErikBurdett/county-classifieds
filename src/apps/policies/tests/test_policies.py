from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from apps.policies.models import PolicyDocument, PolicyDocumentKind, PolicyDocumentStatus

pytestmark = pytest.mark.django_db


def test_draft_documents_are_not_active_or_binding() -> None:
    document = PolicyDocument.objects.create(
        kind=PolicyDocumentKind.TERMS,
        version=1,
        title="Terms — project-owner draft",
        body="DRAFT FOR PROJECT-OWNER REVIEW ONLY.",
    )

    assert document.status == PolicyDocumentStatus.DRAFT


def test_active_document_requires_named_legal_entity() -> None:
    document = PolicyDocument(
        kind=PolicyDocumentKind.PRIVACY,
        version=1,
        title="Privacy",
        body="Reviewed content required.",
        status=PolicyDocumentStatus.ACTIVE,
    )

    with pytest.raises(ValidationError, match="legal entity"):
        document.full_clean()
