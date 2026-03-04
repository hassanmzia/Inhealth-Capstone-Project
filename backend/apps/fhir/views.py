"""
FHIR R4 REST API ViewSets.
Implements FHIR RESTful API: GET /Patient, POST /Patient, GET /Patient/{id}, etc.
"""

import logging

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
        return self.request.user.tenant

    def get_fhir_service(self):
        return FHIRService(self.get_tenant())

    def list(self, request):
        """FHIR search — GET /fhir/{ResourceType}"""
        qs = self.get_queryset()
        serializer = self.get_serializer(qs, many=True)
        service = self.get_fhir_service()
        from django.conf import settings
        bundle = service.build_fhir_bundle(
            self.resource_type,
            list(qs),
            qs.count(),
            f"{settings.FHIR_BASE_URL}",
        )
        return Response(bundle)

    def retrieve(self, request, pk=None):
        """FHIR read — GET /fhir/{ResourceType}/{id}"""
        service = self.get_fhir_service()
        resource = service.get_resource(self.resource_type, pk)
        if resource is None:
            return Response(
                service.build_operation_outcome("error", "not-found", f"{self.resource_type}/{pk} not found"),
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(resource)
        return Response(serializer.data)

    def create(self, request):
        """FHIR create — POST /fhir/{ResourceType}"""
        service = self.get_fhir_service()
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
        instance = serializer.save(tenant=self.get_tenant())
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
            qs = qs.filter(code=params["code"])
        if params.get("date"):
            qs = qs.filter(effective_datetime__date=params["date"])
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
        if self.request.query_params.get("patient"):
            qs = qs.filter(patient__fhir_id=self.request.query_params["patient"])
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        return qs


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
