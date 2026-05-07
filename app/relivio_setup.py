from __future__ import annotations

import os
from contextvars import ContextVar
from typing import Optional

from dotenv import load_dotenv
from relivio import Relivio

load_dotenv()

request_id_var: ContextVar[Optional[str]] = ContextVar(
    "relivio_request_id",
    default=None,
)

relivio = Relivio(
    api_key=os.environ["RELIVIO_PROJECT_API_KEY"],
    base_url=os.environ["RELIVIO_API_BASE_URL"],
    default_service=os.getenv("RELIVIO_SERVICE_NAME", "relivio-demo-fastapi"),
    trace_id_provider=request_id_var.get,
)
