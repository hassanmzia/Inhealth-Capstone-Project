"""
FHIR R4 REST API ViewSets.
Implements FHIR RESTful API: GET /Patient, POST /Patient, GET /Patient/{id}, etc.
"""

import logging

from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts.permissions import CanAccessPHI, IsClinician

from .models import (
    FHIRAllergyIntolerance,
    FHIRAppointment,
    FHIRCarePlan,
    FHIRCondition,
    FHIRDiagnosticReport,
    FHIRDocumentReference,
    FHIREncounter,
    FHIRImmunization,
    FHIRMedicationRequest,
    FHIRObservation,
    FHIRPatient,
)
from .serializers import (
    FHIRAllergyIntoleranceSerializer,
    FHIRAppointmentSerializer,
    FHIRCarePlanSerializer,
    FHIRConditionSerializer,
    FHIRDiagnosticReportSerializer,
    FHIRDocumentReferenceSerializer,
    FHIREncounterSerializer,
    FHIRImmunizationSerializer,
    FHIRMedicationRequestSerializer,
    FHIRObservationSerializer,
    FHIRPatientSerializer,
)
from .services import FHIRService
from .validators import FHIRValidationError

logger = logging.getLogger("apps.fhir")


class FHIRBaseViewSet(GenericViewSet):
    """
    Base FHIR ViewSet implementing FHIR R4 REST interaction patterns.
    Subclasses specify the resource type and model.
    """

    permission_classes = [CanAccessPHI]
    resource_type = None  # Override in subclasses

    def get_tenant(self):
        return (getattr(self.request, 'tenant', None) or self.request.user.tenant)

    def get_fhir_service(self):
        return FHIRService(self.get_tenant())

    def list(self, request):
        """FHIR search — GET /fhir/{ResourceType}"""
        qs = self.get_queryset()
        service = self.get_fhir_service()
        serializer = self.get_serializer(qs, many=True)
        from django.conf import settings
        base_url = f"{settings.FHIR_BASE_URL}"
        entries = []
        for resource_data, obj in zip(serializer.data, qs):
            entries.append({
                "fullUrl": f"{base_url}/{self.resource_type}/{obj.fhir_id}",
                "resource": resource_data,
            })
        return Response({
            "resourceType": "Bundle",
            "type": "searchset",
            "total": len(entries),
            "link": [{"relation": "self", "url": f"{base_url}/{self.resource_type}"}],
            "entry": entries,
        })

    def retrieve(self, request, pk=None):
        """FHIR read — GET /fhir/{ResourceType}/{id}"""
        service = self.get_fhir_service()
        # Try lookup by fhir_id first, then fall back to DB primary key
        resource = service.get_resource(self.resource_type, pk)
        if resource is None:
            model = service.get_model(self.resource_type)
            try:
                resource = model.objects.get(pk=pk, tenant=service.tenant)
            except (model.DoesNotExist, ValueError):
                return Response(
                    service.build_operation_outcome("error", "not-found", f"{self.resource_type}/{pk} not found"),
                    status=status.HTTP_404_NOT_FOUND,
                )
        try:
            serializer = self.get_serializer(resource)
            return Response(serializer.data)
        except Exception:
            logger.exception("Failed to serialize %s/%s", self.resource_type, pk)
            # Fall back to raw_resource if serializer fails
            if resource.raw_resource:
                return Response(resource.raw_resource)
            return Response(
                service.build_operation_outcome("error", "exception", f"Failed to serialize {self.resource_type}/{pk}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request):
        """FHIR create — POST /fhir/{ResourceType}"""
        try:
            service = self.get_fhir_service()
        except Exception:
            logger.exception("Failed to initialize FHIR service for create")
            return Response(
                {"error": "Unable to resolve tenant context"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Only run FHIR R4 validation on standard FHIR JSON payloads
        if request.data.get("resourceType"):
            try:
                service.validate(self.resource_type, request.data)
            except FHIRValidationError as e:
                return Response(
                    service.build_operation_outcome(
                        "error", "invalid",
                        "; ".join(f"{err['path']}: {err['message']}" for err in e.errors)
                    ),
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            instance = serializer.save(tenant=self.get_tenant())
        except Exception:
            logger.exception(
                "Failed to save %s resource: %s",
                self.resource_type, serializer.validated_data,
            )
            return Response(
                service.build_operation_outcome(
                    "error", "exception",
                    f"Failed to create {self.resource_type} resource",
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers={
                **headers,
                "Location": f"{self.resource_type}/{instance.fhir_id}",
                "ETag": f'W/"{instance.meta_version_id}"',
            },
        )

    def update(self, request, pk=None, partial=False):
        """FHIR update — PUT/PATCH /fhir/{ResourceType}/{id}"""
        service = self.get_fhir_service()
        resource = service.get_resource(self.resource_type, pk)
        if resource is None:
            return Response(
                service.build_operation_outcome("error", "not-found", f"{self.resource_type}/{pk} not found"),
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(resource, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, headers={"ETag": f'W/"{resource.meta_version_id}"'})

    def destroy(self, request, pk=None):
        """FHIR delete — DELETE /fhir/{ResourceType}/{id}"""
        service = self.get_fhir_service()
        resource = service.get_resource(self.resource_type, pk)
        if resource is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        resource.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_success_headers(self, data):
        return {}


class FHIRPatientViewSet(FHIRBaseViewSet):
    serializer_class = FHIRPatientSerializer
    resource_type = "Patient"

    def get_queryset(self):
        qs = FHIRPatient.objects.filter(tenant=self.get_tenant()).select_related("primary_care_provider")
        # FHIR search parameters
        params = self.request.query_params
        if params.get("family"):
            qs = qs.filter(last_name__icontains=params["family"])
        if params.get("given"):
            qs = qs.filter(first_name__icontains=params["given"])
        if params.get("birthdate"):
            qs = qs.filter(birth_date=params["birthdate"])
        if params.get("identifier"):
            qs = qs.filter(mrn=params["identifier"])
        if params.get("active"):
            qs = qs.filter(active=params["active"].lower() == "true")
        return qs

    @action(detail=True, methods=["get"])
    def everything(self, request, pk=None):
        """FHIR $everything operation — all resources for a patient."""
        service = self.get_fhir_service()
        patient = service.get_resource("Patient", pk)
        if not patient:
            return Response(status=status.HTTP_404_NOT_FOUND)

        entries = []
        entries.append({"resource": FHIRPatientSerializer(patient).data})

        for obs in FHIRObservation.objects.filter(patient=patient).order_by("-effective_datetime")[:50]:
            entries.append({"resource": FHIRObservationSerializer(obs).data})
        for cond in FHIRCondition.objects.filter(patient=patient):
            entries.append({"resource": FHIRConditionSerializer(cond).data})
        for med in FHIRMedicationRequest.objects.filter(patient=patient, status="active"):
            entries.append({"resource": FHIRMedicationRequestSerializer(med).data})
        for allergy in FHIRAllergyIntolerance.objects.filter(patient=patient):
            entries.append({"resource": FHIRAllergyIntoleranceSerializer(allergy).data})
        for encounter in FHIREncounter.objects.filter(patient=patient).order_by("-period_start")[:20]:
            entries.append({"resource": FHIREncounterSerializer(encounter).data})
        for report in FHIRDiagnosticReport.objects.filter(patient=patient).order_by("-effective_datetime")[:20]:
            entries.append({"resource": FHIRDiagnosticReportSerializer(report).data})
        for doc in FHIRDocumentReference.objects.filter(patient=patient).order_by("-date")[:20]:
            entries.append({"resource": FHIRDocumentReferenceSerializer(doc).data})

        from django.utils import timezone
        return Response({
            "resourceType": "Bundle",
            "type": "searchset",
            "total": len(entries),
            "meta": {"lastUpdated": timezone.now().isoformat()},
            "entry": entries,
        })


class FHIRObservationViewSet(FHIRBaseViewSet):
    serializer_class = FHIRObservationSerializer
    resource_type = "Observation"

    def get_queryset(self):
        qs = FHIRObservation.objects.filter(tenant=self.get_tenant()).select_related("patient")
        params = self.request.query_params
        if params.get("patient"):
            qs = qs.filter(patient__fhir_id=params["patient"])
        if params.get("code"):
            codes = params["code"].split(",")
            qs = qs.filter(code__in=codes) if len(codes) > 1 else qs.filter(code=codes[0])
        if params.get("date"):
            date_val = params["date"]
            # Support FHIR date prefixes: ge (>=), le (<=), gt (>), lt (<)
            if date_val.startswith("ge"):
                qs = qs.filter(effective_datetime__gte=date_val[2:])
            elif date_val.startswith("le"):
                qs = qs.filter(effective_datetime__lte=date_val[2:])
            elif date_val.startswith("gt"):
                qs = qs.filter(effective_datetime__gt=date_val[2:])
            elif date_val.startswith("lt"):
                qs = qs.filter(effective_datetime__lt=date_val[2:])
            else:
                qs = qs.filter(effective_datetime__date=date_val)
        return qs.order_by("-effective_datetime")


class FHIRConditionViewSet(FHIRBaseViewSet):
    serializer_class = FHIRConditionSerializer
    resource_type = "Condition"

    def get_queryset(self):
        qs = FHIRCondition.objects.filter(tenant=self.get_tenant()).select_related("patient")
        params = self.request.query_params
        if params.get("patient"):
            qs = qs.filter(patient__fhir_id=params["patient"])
        if params.get("code"):
            qs = qs.filter(code=params["code"])
        if params.get("clinical-status"):
            qs = qs.filter(clinical_status=params["clinical-status"])
        return qs


class FHIRMedicationRequestViewSet(FHIRBaseViewSet):
    serializer_class = FHIRMedicationRequestSerializer
    resource_type = "MedicationRequest"

    def get_queryset(self):
        qs = FHIRMedicationRequest.objects.filter(tenant=self.get_tenant()).select_related("patient")
        params = self.request.query_params
        if params.get("patient"):
            qs = qs.filter(patient__fhir_id=params["patient"])
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        return qs


class FHIRAllergyIntoleranceViewSet(FHIRBaseViewSet):
    serializer_class = FHIRAllergyIntoleranceSerializer
    resource_type = "AllergyIntolerance"

    def get_queryset(self):
        qs = FHIRAllergyIntolerance.objects.filter(tenant=self.get_tenant()).select_related("patient")
        if self.request.query_params.get("patient"):
            qs = qs.filter(patient__fhir_id=self.request.query_params["patient"])
        return qs


class FHIRAppointmentViewSet(FHIRBaseViewSet):
    serializer_class = FHIRAppointmentSerializer
    resource_type = "Appointment"

    def get_queryset(self):
        qs = FHIRAppointment.objects.filter(tenant=self.get_tenant()).select_related("patient")
        params = self.request.query_params
        if params.get("patient"):
            qs = qs.filter(patient__fhir_id=params["patient"])
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("date"):
            qs = qs.filter(start__date=params["date"])
        return qs.order_by("-start")


class FHIRCarePlanViewSet(FHIRBaseViewSet):
    serializer_class = FHIRCarePlanSerializer
    resource_type = "CarePlan"

    def get_queryset(self):
        qs = FHIRCarePlan.objects.filter(tenant=self.get_tenant()).select_related("patient")
        patient_param = self.request.query_params.get("patient")
        if patient_param:
            # Accept both internal UUID (from patient detail page) and FHIR ID
            qs = qs.filter(
                Q(patient_id=patient_param) | Q(patient__fhir_id=patient_param)
            )
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        return qs.order_by("-created_at")


class FHIREncounterViewSet(FHIRBaseViewSet):
    serializer_class = FHIREncounterSerializer
    resource_type = "Encounter"

    def get_queryset(self):
        qs = FHIREncounter.objects.filter(tenant=self.get_tenant()).select_related("patient")
        if self.request.query_params.get("patient"):
            qs = qs.filter(patient__fhir_id=self.request.query_params["patient"])
        return qs.order_by("-period_start")


class FHIRImmunizationViewSet(FHIRBaseViewSet):
    serializer_class = FHIRImmunizationSerializer
    resource_type = "Immunization"

    def get_queryset(self):
        qs = FHIRImmunization.objects.filter(tenant=self.get_tenant()).select_related("patient")
        if self.request.query_params.get("patient"):
            qs = qs.filter(patient__fhir_id=self.request.query_params["patient"])
        return qs.order_by("-occurrence_datetime")


class FHIRDiagnosticReportViewSet(FHIRBaseViewSet):
    serializer_class = FHIRDiagnosticReportSerializer
    resource_type = "DiagnosticReport"

    def get_queryset(self):
        qs = FHIRDiagnosticReport.objects.filter(tenant=self.get_tenant()).select_related("patient")
        params = self.request.query_params
        if params.get("patient"):
            qs = qs.filter(patient__fhir_id=params["patient"])
        if params.get("category"):
            qs = qs.filter(category_code=params["category"])
        if params.get("code"):
            qs = qs.filter(code=params["code"])
        if params.get("date"):
            qs = qs.filter(effective_datetime__date=params["date"])
        return qs.order_by("-effective_datetime")


class FHIRDocumentReferenceViewSet(FHIRBaseViewSet):
    serializer_class = FHIRDocumentReferenceSerializer
    resource_type = "DocumentReference"

    def get_queryset(self):
        qs = FHIRDocumentReference.objects.filter(tenant=self.get_tenant()).select_related("patient")
        params = self.request.query_params
        if params.get("patient"):
            qs = qs.filter(patient__fhir_id=params["patient"])
        if params.get("type"):
            qs = qs.filter(type_code=params["type"])
        if params.get("category"):
            qs = qs.filter(category=params["category"])
        return qs.order_by("-date")
