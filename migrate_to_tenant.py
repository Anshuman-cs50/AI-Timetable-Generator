from app import create_app, db
from app.models import User, Department, Faculty, Course, StudentGroup, Room, Subject, TimetableEntry, SystemSetting, TimeSlot

app = create_app()

def migrate_to_tenant():
    with app.app_context():
        # 1. Create default user if not exists
        admin = User.query.filter_by(username='admin_institution').first()
        if not admin:
            admin = User(username='admin_institution')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print(f"Created default user: admin_institution")
        
        user_id = admin.id
        
        # 2. Update all orphan records
        models = [Department, Faculty, Course, StudentGroup, Room, Subject, TimetableEntry, SystemSetting, TimeSlot]
        
        for model in models:
            orphans = model.query.filter_by(user_id=None).all()
            if orphans:
                print(f"Migrating {len(orphans)} records for {model.__name__}...")
                for record in orphans:
                    record.user_id = user_id
                db.session.commit()

        print("Data migration complete.")

if __name__ == "__main__":
    migrate_to_tenant()
