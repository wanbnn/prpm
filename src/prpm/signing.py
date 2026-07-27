from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Any

import keyring
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from keyring.errors import KeyringError

from prpm.errors import PrpmError

KEY_SERVICE = "prpm:signing"
KEY_USERNAME = "ed25519:default"


@dataclass(frozen=True)
class SigningIdentity:
    private_key: Ed25519PrivateKey
    public_key: bytes
    key_id: str
    persistent: bool = True

    def sign(self, payload: bytes) -> str:
        return base64.b64encode(self.private_key.sign(payload)).decode("ascii")


def canonical_json(document: dict[str, Any]) -> bytes:
    return json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _identity(
    private_key: Ed25519PrivateKey, persistent: bool = True
) -> SigningIdentity:
    public = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    key_id = "ed25519:" + hashlib.sha256(public).hexdigest()[:24]
    return SigningIdentity(private_key, public, key_id, persistent)


def generate_identity(force: bool = False) -> SigningIdentity:
    if not force:
        existing = load_identity(required=False)
        if existing is not None:
            return existing
    private_key = Ed25519PrivateKey.generate()
    raw = private_key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    try:
        keyring.set_password(
            KEY_SERVICE,
            KEY_USERNAME,
            base64.b64encode(raw).decode("ascii"),
        )
    except KeyringError:
        return _identity(private_key, persistent=False)
    return _identity(private_key)


def load_identity(required: bool = True) -> SigningIdentity | None:
    try:
        encoded = keyring.get_password(KEY_SERVICE, KEY_USERNAME)
    except KeyringError as exc:
        if not required:
            return None
        raise PrpmError("Não foi possível acessar a chave no keyring.") from exc
    if not encoded:
        if required:
            raise PrpmError("Nenhuma chave de assinatura. Execute `prpm key generate`.")
        return None
    try:
        private_key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(encoded))
    except (ValueError, TypeError) as exc:
        raise PrpmError("A chave guardada no keyring é inválida.") from exc
    return _identity(private_key)


def public_key_text(identity: SigningIdentity) -> str:
    return base64.b64encode(identity.public_key).decode("ascii")


def public_key_id(public_key_value: str) -> str:
    try:
        public = base64.b64decode(public_key_value)
    except (ValueError, TypeError) as exc:
        raise PrpmError("Chave pública inválida no manifesto.") from exc
    if len(public) != 32:
        raise PrpmError("Chave pública Ed25519 precisa ter 32 bytes.")
    return "ed25519:" + hashlib.sha256(public).hexdigest()[:24]


def verify_signature(
    payload: bytes,
    signature_text: str,
    public_key_value: str,
) -> bool:
    try:
        public_key = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(public_key_value)
        )
        public_key.verify(base64.b64decode(signature_text), payload)
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False
