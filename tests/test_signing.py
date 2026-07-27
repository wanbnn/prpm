from prpm import signing


def test_signing_identity_round_trip(monkeypatch):
    values = {}
    monkeypatch.setattr(
        signing.keyring,
        "set_password",
        lambda service, user, value: values.__setitem__((service, user), value),
    )
    monkeypatch.setattr(
        signing.keyring,
        "get_password",
        lambda service, user: values.get((service, user)),
    )

    identity = signing.generate_identity()
    payload = b'{"package":"demo"}'
    signature = identity.sign(payload)

    assert signing.load_identity().key_id == identity.key_id
    assert signing.verify_signature(
        payload,
        signature,
        signing.public_key_text(identity),
    )
    assert not signing.verify_signature(
        b"tampered",
        signature,
        signing.public_key_text(identity),
    )


def test_canonical_json_is_order_independent():
    assert signing.canonical_json({"b": 2, "a": 1}) == signing.canonical_json(
        {"a": 1, "b": 2}
    )

