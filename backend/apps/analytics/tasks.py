"""Celery tasks for analytics and population health."""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("apps.analytics")


@shared_task
def generate_population_analytics():
    """
    Refresh all population health KPIs for all active tenants.
    Runs every hour.
    """
    from apps.tenants.models import Organization
    from .models import ClinicalKPI
    from apps.fhir.models import FHIRPatient, FHIRObservation, FHIRCondition

    tenants = Organization.objects.filter(is_active=True)
    updated_count = 0

    for tenant in tenants:
        today = timezone.now().date()

        try:
            # Avg A1C for diabetic patients
            avg_a1c = FHIRObservation.objects.filter(
                tenant=tenant,
                code="4548-4",
                effective_datetime__date__gte=today - timedelta(days=90),
            ).aggregate(avg=__import__("django.db.models", fromlist=["Avg"]).Avg("value_quantity"))["avg"]

            if avg_a1c:
                ClinicalKPI.objects.update_or_create(
                    tenant=tenant,
                    metric_name="avg_a1c",
                    metric_date=today,
                    defaults={"metric_value": round(avg_a1c, 2), "unit": "%"},
                )
                updated_count += 1

            # % patients with A1C < 8
            total_a1c = FHIRObservation.objects.filter(
                tenant=tenant,
                code="4548-4",
                effective_datetime__date__gte=today - timedelta(days=90),
            ).count()

            controlled_a1c = FHIRObservation.objects.filter(
                tenant=tenant,
                code="4548-4",
                effective_datetime__date__gte=today - timedelta(days=90),
                value_quantity__lt=8.0,
            ).count()

            if total_a1c > 0:
                pct = (controlled_a1c / total_a1c) * 100
                ClinicalKPI.objects.update_or_create(
                    tenant=tenant,
                    metric_name="pct_a1c_controlled",
                    metric_date=today,
                    defaults={"metric_value": round(pct, 1), "unit": "%"},
                )
                updated_count += 1

        except Exception as e:
            logger.error(f"KPI generation error for tenant {tenant.slug}: {e}")

    logger.info(f"Population analytics complete. Updated {updated_count} KPIs.")
    return {"updated_kpis": updated_count}


@shared_task(bind=True, max_retries=2)
def refresh_population_cohort(self, cohort_id: str):
    """Refresh the patient count for a population cohort."""
    from .models import PopulationCohort
    from apps.fhir.models import FHIRPatient, FHIRCondition

    try:
        cohort = PopulationCohort.objects.get(id=cohort_id)
        filters = cohort.condition_filter

        qs = FHIRPatient.objects.filter(tenant=cohort.tenant, active=True)

        if filters.get("icd10_codes"):
            from django.db.models import Q
            q = Q()
            for code in filters["icd10_codes"]:
                q |= Q(conditions__code__startswith=code, conditions__clinical_status="active")
            qs = qs.filter(q).distinct()

        if filters.get("age_min"):
            from datetime import date
            max_birth = date.today().replace(year=date.today().year - filters["age_min"])
            qs = qs.filter(birth_date__lte=max_birth)

        if filters.get("age_max"):
            from datetime import date
            min_birth = date.today().replace(year=date.today().year - filters["age_max"])
            qs = qs.filter(birth_date__gte=min_birth)

        cohort.patient_count = qs.count()
        cohort.last_refreshed = timezone.now()
        cohort.save(update_fields=["patient_count", "last_refreshed"])

        return {"cohort_id": cohort_id, "patient_count": cohort.patient_count}

    except PopulationCohort.DoesNotExist:
        logger.error(f"Cohort {cohort_id} not found")
    except Exception as exc:
        logger.error(f"Cohort refresh failed: {exc}")
        raise self.retry(exc=exc)


@shared_task
def compute_risk_scores_batch(tenant_id: str = None):
    """
    Compute risk scores for all patients in the given tenant (or all tenants).
    Uses XGBoost model from ml/ module.
    """
    from apps.fhir.models import FHIRPatient
    from .models import RiskScore
    from datetime import timedelta

    try:
        from ml.xgboost_risk import XGBoostRiskModel
        model = XGBoostRiskModel()
    except Exception as e:
        logger.error(f"Could not load risk model: {e}")
        return

    qs = FHIRPatient.objects.filter(active=True)
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)

    scored = 0
    for patient in qs.select_related("tenant"):
        try:
            features = model.extract_features(patient)
            score = model.predict(features)
            RiskScore.objects.create(
                patient=patient,
                tenant=patient.tenant,
                score_type=RiskScore.ScoreType.HOSPITALIZATION_7D,
                score=score,
                features=features,
                model_version=model.version,
                valid_until=timezone.now() + timedelta(hours=24),
            )
            scored += 1
        except Exception as e:
            logger.debug(f"Risk score failed for patient {patient.id}: {e}")

    logger.info(f"Risk scores computed for {scored} patients")
    return {"scored": scored}
