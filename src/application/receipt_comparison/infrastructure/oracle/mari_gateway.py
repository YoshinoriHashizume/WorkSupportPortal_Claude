from __future__ import annotations

from datetime import date

from application.receipt_comparison.infrastructure.oracle import client as oracle_client


class OracleMariRowGateway:
    def fetch_mari_rows(
        self,
        *,
        comparison_type: str,
        supplier: object,
        start_date: date,
        end_date: date,
        receiving_places: list[str],
    ) -> list[object]:
        return oracle_client.fetch_mari_rows(
            comparison_type=comparison_type,
            supplier=supplier,
            start_date=start_date,
            end_date=end_date,
            receiving_places=receiving_places,
        )
