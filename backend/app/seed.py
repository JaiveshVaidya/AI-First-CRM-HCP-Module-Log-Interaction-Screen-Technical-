from .database import SessionLocal, engine, Base
from . import models

def seed_db():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if database is already seeded
        if db.query(models.HCP).count() > 0:
            print("Database already seeded.")
            return

        print("Seeding database...")

        # 1. Seed HCPs
        hcps = [
            models.HCP(
                name="Dr. Smith",
                specialty="Oncology",
                organization="City Cancer Center",
                email="smith@citycancer.org",
                phone="555-0192",
                history_notes="Prefers clinical study data over slides. Highly interested in OncoBoost Phase III results."
            ),
            models.HCP(
                name="Dr. John",
                specialty="Cardiology",
                organization="Metro Heart Clinic",
                email="j.doe@metroheart.com",
                phone="555-0143",
                history_notes="Focuses on patient compliance. Prefers physical brochures and patient starter kits."
            ),
            models.HCP(
                name="Dr. Sharma",
                specialty="Immunology",
                organization="University Research Hospital",
                email="asharma@unihosp.edu",
                phone="555-0187",
                history_notes="Advisory board candidate. Extremely knowledgeable in immunotherapy pathways."
            ),
            models.HCP(
                name="Dr. Davis",
                specialty="General Medicine",
                organization="Valley Health Associates",
                email="davis@valleyhealth.com",
                phone="555-0111",
                history_notes="High volume practitioner. Very busy, meetings must be short and direct."
            )
        ]
        db.add_all(hcps)

        # 2. Seed Materials
        materials = [
            models.Material(name="OncoBoost Phase III PDF", type="Clinical Study", product="OncoBoost"),
            models.Material(name="CardioShield Brochure", type="Brochure", product="CardioShield"),
            models.Material(name="ImmunoTrax Slide Deck", type="Presentation", product="ImmunoTrax"),
            models.Material(name="LipiGuard Patient Guide", type="Brochure", product="LipiGuard"),
            models.Material(name="OncoBoost Safety Sheet", type="PDF", product="OncoBoost"),
            models.Material(name="CardioShield Efficacy Report", type="Clinical Study", product="CardioShield")
        ]
        db.add_all(materials)

        # 3. Seed Samples
        samples = [
            models.Sample(name="OncoBoost 10mg Starter Kit", product="OncoBoost", dosage="10mg"),
            models.Sample(name="CardioShield 5mg Sample Pack", product="CardioShield", dosage="5mg"),
            models.Sample(name="ImmunoTrax 50mcg Vial Kit", product="ImmunoTrax", dosage="50mcg"),
            models.Sample(name="LipiGuard 20mg Trial Box", product="LipiGuard", dosage="20mg")
        ]
        db.add_all(samples)

        # 4. Seed Suggested Follow-ups (General and seeded)
        suggested_followups = [
            models.SuggestedFollowUp(hcp_name="Dr. Smith", text="Schedule follow-up meeting in 2 weeks", status="Pending"),
            models.SuggestedFollowUp(hcp_name="Dr. Smith", text="Send OncoBoost Phase III PDF", status="Pending"),
            models.SuggestedFollowUp(hcp_name="Dr. Sharma", text="Add Dr. Sharma to advisory board invite list", status="Pending"),
            models.SuggestedFollowUp(hcp_name="Dr. John", text="Provide CardioShield 5mg Sample Pack", status="Pending")
        ]
        db.add_all(suggested_followups)

        db.commit()
        print("Database seeding completed successfully.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
