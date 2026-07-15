#!/bin/sh
set -eu

# Escape deployment-provided values before embedding them in JavaScript.
js_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

temporal_url="$(js_escape "${TEMPORAL_BACKEND_URL:-/api/temporal}")"
langgraph_url="$(js_escape "${LANGGRAPH_BACKEND_URL:-/api/langgraph}")"
temporal_langgraph_url="$(js_escape "${TEMPORAL_LANGGRAPH_BACKEND_URL:-/api/temporal-langgraph}")"
default_backend="$(js_escape "${DEFAULT_AGENT_BACKEND:-temporal-langgraph}")"

# Runtime generation lets one frontend image work in local and cloud networks.
cat > /usr/share/nginx/html/config.js <<EOF
window.AGENT_BACKENDS = {
  temporal: {
    label: 'Temporal workflow',
    url: "${temporal_url}",
    poweredBy: 'Powered by Temporal Workflow',
    conversationIdLabel: 'workflowId',
    conversationLinkBase: '',
  },
  'temporal-langgraph': {
    label: 'Temporal + LangGraph workflow',
    url: "${temporal_langgraph_url}",
    poweredBy: 'Powered by Temporal + LangGraph',
    conversationIdLabel: 'workflowId',
    conversationLinkBase: '',
  },
  langgraph: {
    label: 'LangGraph standalone',
    url: "${langgraph_url}",
    poweredBy: 'Powered by LangGraph',
    conversationIdLabel: 'conversationId',
    conversationLinkBase: '',
  },
};

window.DEFAULT_AGENT_BACKEND = "${default_backend}";
EOF
