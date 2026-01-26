#!/usr/bin/env python
"""
Script to verify and ensure the Feature Requestor app exists in the database.
Run this script to check if the app is registered and create it if missing.
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import the app
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app, db
from app.models import App, User

def verify_feature_requestor_app():
    """Verify that the Feature Requestor app exists in the database."""
    app = create_app()
    
    with app.app_context():
        # Check if the app exists
        feature_requestor_app = App.query.filter_by(app_name='feature-requestor').first()
        
        if feature_requestor_app:
            print(f"✓ Feature Requestor app found in database:")
            print(f"  - ID: {feature_requestor_app.id}")
            print(f"  - Display Name: {feature_requestor_app.app_display_name}")
            print(f"  - Description: {feature_requestor_app.app_description}")
            print(f"  - Icon Path: {feature_requestor_app.icon_path or 'None'}")
            print(f"  - App URL: {feature_requestor_app.app_url or 'None'}")
            return True
        else:
            print("✗ Feature Requestor app NOT found in database!")
            print("Creating the app now...")
            
            # Get admin user
            admin = User.query.filter_by(role='admin').first()
            if not admin:
                print("✗ ERROR: No admin user found! Cannot create app.")
                return False
            
            # Create the app
            feature_requestor_app = App(
                app_name='feature-requestor',
                app_display_name='Feature Requestor',
                app_description='The Feature Requestor application itself - request features for this platform!',
                app_url='',
                github_url='',
                app_owner_id=admin.id
            )
            
            db.session.add(feature_requestor_app)
            db.session.commit()
            
            print(f"✓ Feature Requestor app created successfully!")
            print(f"  - ID: {feature_requestor_app.id}")
            print(f"  - Display Name: {feature_requestor_app.app_display_name}")
            
            # Check if icon file exists
            instance_path = Path(__file__).parent / 'instance' / 'uploads'
            icon_filename = f'app_{feature_requestor_app.id}_icon.png'
            icon_path = instance_path / icon_filename
            
            if icon_path.exists():
                print(f"  - Icon file found: {icon_path}")
                feature_requestor_app.icon_path = f'uploads/{icon_filename}'
                db.session.commit()
                print(f"  - Icon path updated in database")
            else:
                # Check for icon.png in instance folder
                instance_icon = Path(__file__).parent / 'instance' / 'icon.png'
                if instance_icon.exists():
                    print(f"  - Found icon.png in instance folder, copying to uploads...")
                    instance_path.mkdir(parents=True, exist_ok=True)
                    import shutil
                    shutil.copy(instance_icon, icon_path)
                    feature_requestor_app.icon_path = f'uploads/{icon_filename}'
                    db.session.commit()
                    print(f"  - Icon copied and path updated")
            
            return True

if __name__ == '__main__':
    try:
        verify_feature_requestor_app()
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

