# API Documentation

The InHealth platform auto-generates interactive API documentation via **Swagger UI / OpenAPI 3.0**.

**Live Docs**: [http://localhost:8000/api/v1/docs/](http://localhost:8000/api/v1/docs/)

- Swagger UI is served by `drf-spectacular` from the Django backend.
- All endpoints require JWT authentication (pass your `access` token via the **Authorize** button).
- FHIR R4 resources are available under `/api/v1/fhir/`.
- Clinical, billing, and patient management endpoints live under `/api/v1/`.
