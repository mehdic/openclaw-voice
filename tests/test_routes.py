from __future__ import annotations


def test_health_returns_status_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_api_session_returns_authenticated_true_in_demo_mode(client):
    response = client.get("/api/session")

    payload = response.get_json()

    assert response.status_code == 200
    assert payload["authenticated"] is True
    assert payload["authMode"] == "demo"
    assert payload["defaultAgent"] == "test-agent"


def test_api_agents_returns_agent_list(client):
    response = client.get("/api/agents")

    payload = response.get_json()

    assert response.status_code == 200
    assert payload["defaultAgent"] == "test-agent"
    assert payload["agents"] == [
        {
            "displayName": "Test Agent",
            "emoji": "T",
            "id": "test-agent",
            "language": "en",
            "model": "gateway-default",
            "models": [
                "openai/gpt-4.1-mini",
                "anthropic/claude-3-5-sonnet",
                "google/gemini-2.0-flash",
            ],
        }
    ]


def test_api_token_returns_valid_token_data(client):
    response = client.get("/api/token?agent=test-agent&session=abc123")

    payload = response.get_json()

    assert response.status_code == 200
    assert payload == {
        "agent": "test-agent",
        "model": "openai/gpt-4.1-mini",
        "participantToken": "jwt:user-demo-example-com",
        "room": "voice-test-agent-abc123",
        "serverUrl": "wss://livekit.example.test",
        "sessionId": "abc123",
    }


def test_api_token_rejects_disallowed_agent(client):
    response = client.get("/api/token?agent=other-agent")

    assert response.status_code == 403
    assert response.get_json() == {"error": "Agent not allowed"}


def test_api_command_help_returns_commands(client):
    response = client.post("/api/command", json={"command": "/help"})

    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["kind"] == "help"
    assert any(item["command"] == "/help" for item in payload["commands"])


def test_api_command_agent_without_args_returns_agent_list(client):
    response = client.post("/api/command", json={"command": "/agent"})

    payload = response.get_json()

    assert response.status_code == 200
    assert payload["kind"] == "agents"
    assert payload["current"] == "test-agent"
    assert payload["buttons"] == [{"label": "test-agent", "value": "/agent test-agent"}]


def test_api_command_unknown_command_returns_400(client):
    response = client.post("/api/command", json={"command": "/unknown"})

    assert response.status_code == 400
    assert response.get_json() == {"error": "Unknown command: /unknown"}
