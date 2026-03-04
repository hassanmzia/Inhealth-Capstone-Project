"""
HL7 v2 parser for InHealth.
Parses ADT, ORU, ORM messages into structured Python dicts.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("apps.hl7")


@dataclass
class HL7Segment:
    """Represents a single HL7 v2 segment."""
    segment_id: str
    fields: List[str]

    def get_field(self, index: int, default: str = "") -> str:
        try:
            return self.fields[index] or default
        except IndexError:
            return default

    def get_component(self, field_index: int, component_index: int, default: str = "") -> str:
        try:
            field_val = self.fields[field_index]
            if not field_val:
                return default
            components = field_val.split("^")
            return components[component_index] if len(components) > component_index else default
        except IndexError:
            return default


@dataclass
class HL7Message:
    """Parsed HL7 v2 message."""
    raw: str
    segments: List[HL7Segment] = field(default_factory=list)
    field_separator: str = "|"
    component_separator: str = "^"
    subcomponent_separator: str = "&"
    repetition_separator: str = "~"
    escape_character: str = "\\"

    def get_segment(self, segment_id: str) -> Optional[HL7Segment]:
        for seg in self.segments:
            if seg.segment_id == segment_id:
                return seg
        return None

    def get_all_segments(self, segment_id: str) -> List[HL7Segment]:
        return [s for s in self.segments if s.segment_id == segment_id]

    @property
    def message_type(self) -> str:
        msh = self.get_segment("MSH")
        if not msh:
            return ""
        return msh.get_component(8, 0)  # MSH.9.1

    @property
    def message_event(self) -> str:
        msh = self.get_segment("MSH")
        if not msh:
            return ""
        return msh.get_component(8, 1)  # MSH.9.2

    @property
    def message_control_id(self) -> str:
        msh = self.get_segment("MSH")
        if not msh:
            return ""
        return msh.get_field(9)

    @property
    def sending_application(self) -> str:
        msh = self.get_segment("MSH")
        if not msh:
            return ""
        return msh.get_component(2, 0)

    @property
    def sending_facility(self) -> str:
        msh = self.get_segment("MSH")
        if not msh:
            return ""
        return msh.get_component(3, 0)


class HL7Parser:
    """
    HL7 v2 parser.
    Parses standard HL7 v2 messages (MLLP or plain) into structured objects.
    """

    MLLP_START = b"\x0b"
    MLLP_END = b"\x1c\x0d"

    def parse(self, raw_message: str) -> HL7Message:
        """Parse a raw HL7 v2 string into an HL7Message object."""
        # Strip MLLP framing if present
        if isinstance(raw_message, bytes):
            raw_message = raw_message.strip(b"\x0b\x1c\x0d").decode("utf-8", errors="replace")

        raw_message = raw_message.strip()
        if not raw_message:
            raise ValueError("Empty HL7 message")

        # Detect encoding from MSH segment
        lines = [line for line in re.split(r"\r\n|\r|\n", raw_message) if line.strip()]
        if not lines or not lines[0].startswith("MSH"):
            raise ValueError("HL7 message must begin with MSH segment")

        msh_line = lines[0]
        field_sep = msh_line[3] if len(msh_line) > 3 else "|"
        encoding_chars = msh_line[4:8] if len(msh_line) > 7 else "^~\\&"
        component_sep = encoding_chars[0] if len(encoding_chars) > 0 else "^"
        repetition_sep = encoding_chars[1] if len(encoding_chars) > 1 else "~"
        escape_char = encoding_chars[2] if len(encoding_chars) > 2 else "\\"
        subcomponent_sep = encoding_chars[3] if len(encoding_chars) > 3 else "&"

        msg = HL7Message(
            raw=raw_message,
            field_separator=field_sep,
            component_separator=component_sep,
            repetition_separator=repetition_sep,
            escape_character=escape_char,
            subcomponent_separator=subcomponent_sep,
        )

        for line in lines:
            if not line.strip():
                continue
            segment_parts = line.split(field_sep)
            segment_id = segment_parts[0]
            # MSH segment: field 1 IS the separator, so fields start at index 1
            if segment_id == "MSH":
                fields = [field_sep] + segment_parts[1:]
            else:
                fields = segment_parts[1:]
            msg.segments.append(HL7Segment(segment_id=segment_id, fields=fields))

        return msg

    def extract_patient_data(self, msg: HL7Message) -> Dict:
        """Extract patient demographics from PID segment."""
        pid = msg.get_segment("PID")
        if not pid:
            return {}

        # PID-3: Patient Identifier List (MRN)
        mrn = pid.get_component(2, 0) or pid.get_field(2)

        # PID-5: Patient Name
        last_name = pid.get_component(4, 0)
        first_name = pid.get_component(4, 1)
        middle_name = pid.get_component(4, 2)

        # PID-7: Date/Time of Birth
        birth_date_raw = pid.get_field(6)
        birth_date = self._parse_hl7_date(birth_date_raw)

        # PID-8: Administrative Sex
        gender_map = {"M": "male", "F": "female", "O": "other", "U": "unknown"}
        gender = gender_map.get(pid.get_field(7), "unknown")

        # PID-11: Patient Address
        address_line1 = pid.get_component(10, 0)
        city = pid.get_component(10, 2)
        state = pid.get_component(10, 3)
        postal_code = pid.get_component(10, 4)
        country = pid.get_component(10, 5) or "US"

        # PID-13/14: Phone numbers
        phone_home = pid.get_component(12, 0) if len(pid.fields) > 12 else ""
        phone_work = pid.get_component(13, 0) if len(pid.fields) > 13 else ""

        # PID-19: SSN Number - Patient  (last 4 only for display)
        ssn = pid.get_field(18) if len(pid.fields) > 18 else ""

        return {
            "mrn": mrn,
            "first_name": first_name,
            "last_name": last_name,
            "middle_name": middle_name,
            "birth_date": birth_date,
            "gender": gender,
            "address_line1": address_line1,
            "city": city,
            "state": state,
            "postal_code": postal_code,
            "country": country,
            "phone": phone_home or phone_work,
            "ssn_last4": ssn[-4:] if len(ssn) >= 4 else "",
        }

    def extract_observations(self, msg: HL7Message) -> List[Dict]:
        """Extract observations from OBX segments (ORU messages)."""
        observations = []
        obx_segments = msg.get_all_segments("OBX")

        for obx in obx_segments:
            # OBX-3: Observation Identifier
            loinc_code = obx.get_component(2, 0)
            display = obx.get_component(2, 1)
            code_system = obx.get_component(2, 2) or "LN"

            # OBX-4: Sub-ID
            # OBX-5: Observation Value
            value_type = obx.get_field(1)  # NM, ST, CWE, etc.
            value_raw = obx.get_field(4)

            value_quantity = None
            value_string = ""
            if value_type == "NM":
                try:
                    value_quantity = float(value_raw)
                except (ValueError, TypeError):
                    value_string = value_raw
            else:
                value_string = value_raw

            # OBX-6: Units
            unit = obx.get_component(5, 0)

            # OBX-7: Reference Range
            ref_range = obx.get_field(6)
            ref_low = ref_high = None
            if ref_range and "-" in ref_range:
                parts = ref_range.split("-")
                try:
                    ref_low = float(parts[0].strip())
                    ref_high = float(parts[1].strip())
                except (ValueError, IndexError):
                    pass

            # OBX-8: Abnormal Flags
            interpretation = obx.get_field(7)

            # OBX-11: Observation Result Status
            status_map = {"F": "final", "P": "preliminary", "C": "corrected", "X": "cancelled"}
            status = status_map.get(obx.get_field(10), "final")

            # OBX-14: Date/Time of Observation
            obs_datetime = self._parse_hl7_datetime(obx.get_field(13)) if len(obx.fields) > 13 else None

            observations.append({
                "code": loinc_code,
                "display": display,
                "code_system": "http://loinc.org" if code_system in ("LN", "LOINC") else code_system,
                "value_quantity": value_quantity,
                "value_unit": unit,
                "value_string": value_string,
                "reference_range_low": ref_low,
                "reference_range_high": ref_high,
                "interpretation": interpretation,
                "status": status,
                "effective_datetime": obs_datetime,
            })

        return observations

    def extract_orders(self, msg: HL7Message) -> List[Dict]:
        """Extract orders from ORC/OBR segments (ORM messages)."""
        orders = []
        orc_segments = msg.get_all_segments("ORC")

        for orc in orc_segments:
            order_control = orc.get_field(0)  # NW=new, CA=cancel, etc.
            placer_order_number = orc.get_field(1)
            filler_order_number = orc.get_field(2)
            order_status = orc.get_field(4)

            orders.append({
                "order_control": order_control,
                "placer_order_number": placer_order_number,
                "filler_order_number": filler_order_number,
                "order_status": order_status,
            })

        return orders

    @staticmethod
    def _parse_hl7_date(date_str: str) -> Optional[str]:
        """Parse HL7 date format YYYYMMDD to YYYY-MM-DD."""
        if not date_str or len(date_str) < 8:
            return None
        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except Exception:
            return None

    @staticmethod
    def _parse_hl7_datetime(dt_str: str):
        """Parse HL7 datetime format YYYYMMDDHHMMSS."""
        if not dt_str or len(dt_str) < 8:
            return None
        from django.utils import timezone as tz
        from datetime import datetime
        try:
            if len(dt_str) >= 14:
                dt = datetime(int(dt_str[:4]), int(dt_str[4:6]), int(dt_str[6:8]),
                              int(dt_str[8:10]), int(dt_str[10:12]), int(dt_str[12:14]))
            else:
                dt = datetime(int(dt_str[:4]), int(dt_str[4:6]), int(dt_str[6:8]))
            return tz.make_aware(dt)
        except Exception:
            return None

    def build_ack(self, original_msg: HL7Message, ack_code: str = "AA", error_message: str = "") -> str:
        """Build an HL7 ACK message in response to an inbound message."""
        from django.utils import timezone
        import datetime

        msh = original_msg.get_segment("MSH")
        if not msh:
            return ""

        now = timezone.now().strftime("%Y%m%d%H%M%S")
        sending_app = msh.get_component(4, 0) if len(msh.fields) > 4 else "INHEALTH"
        sending_fac = msh.get_component(5, 0) if len(msh.fields) > 5 else "INHEALTH"
        receiving_app = msh.get_component(2, 0)
        receiving_fac = msh.get_component(3, 0)
        control_id = original_msg.message_control_id

        ack_lines = [
            f"MSH|^~\\&|{sending_app}|{sending_fac}|{receiving_app}|{receiving_fac}|{now}||ACK|{control_id}_ACK|P|2.5.1",
            f"MSA|{ack_code}|{control_id}|{error_message}",
        ]
        if error_message and ack_code != "AA":
            ack_lines.append(f"ERR|||207^Application Internal Error|E|{error_message}")

        return "\r".join(ack_lines) + "\r"
