import asyncio

from sqlalchemy import select

from core.database import AsyncSessionLocal
from models.campaign import Campaign
from models.lead import Lead


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(Campaign).where(Campaign.name == "Demo Campaign"))
        campaign = existing.scalars().first()

        if campaign is None:
            campaign = Campaign(
                name="Demo Campaign",
                status="draft",
                settings={
                    "product_name": "Sales Automation Platform",
                    "value_proposition": "Turn leads into meetings without manual follow-ups.",
                    "tone": "Professional",
                },
            )
            session.add(campaign)
            await session.flush()

            leads = [
                Lead(
                    campaign_id=campaign.id,
                    company_name="Acme Logistics",
                    website="https://acme-logistics.example",
                    contact_name="Priya Sharma",
                    email="priya@acme-logistics.example",
                    status="new",
                ),
                Lead(
                    campaign_id=campaign.id,
                    company_name="Northwind Analytics",
                    website="https://northwind-analytics.example",
                    contact_name="Daniel Lee",
                    email="daniel@northwind-analytics.example",
                    status="new",
                ),
                Lead(
                    campaign_id=campaign.id,
                    company_name="Brightlane HR",
                    website="https://brightlane-hr.example",
                    contact_name="Aisha Khan",
                    email="aisha@brightlane-hr.example",
                    status="new",
                ),
            ]
            session.add_all(leads)

        await session.commit()

        print(f"Seeded campaign: {campaign.name} ({campaign.id})")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()

