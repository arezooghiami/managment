from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from DB.database import get_db
from models.ComplaintIssue import ComplaintIssue
from models.branch import Branch, Unit
from models.manager import RegionalManager
from models.user import User


router_branch = APIRouter(prefix="/branches", tags=["Branches"])

@router_branch.post("/create")
def create_branch(
        name: str,
        regional_manager_id: int = None,
        db: Session = Depends(get_db)
):
    """
    ایجاد شعبه جدید

    پارامترها:
    - name: نام شعبه
    - regional_manager_id: شناسه مدیر منطقه (اختیاری)

    بازگشت:
    - اطلاعات شعبه ایجاد شده
    """
    # بررسی وجود شعبه با همان نام
    existing = db.query(Branch).filter(Branch.name == name).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="شعبه با این نام از قبل وجود دارد"
        )

    # بررسی وجود مدیر منطقه
    if regional_manager_id:
        manager = db.query(User).filter(
            User.id == regional_manager_id
        ).first()
        if not manager:
            raise HTTPException(
                status_code=404,
                detail="مدیر منطقه یافت نشد"
            )

    # ایجاد شعبه جدید
    branch = Branch(
        name=name,
        regional_manager_id=regional_manager_id
    )

    db.add(branch)
    db.commit()
    db.refresh(branch)

    return {
        "success": True,
        "message": "شعبه با موفقیت ایجاد شد",
        "data": {
            "branch_id": branch.id,
            "name": branch.name,
            "regional_manager_id": branch.regional_manager_id
        }
    }

# --- روتر واحد سازمانی ---
router_unit = APIRouter(prefix="/units", tags=["Units"])

@router_unit.post("/create")
def create_unit(
        name: str,

        db: Session = Depends(get_db)
):

    existing = db.query(Unit).filter(Unit.name == name).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="واحد با این نام از قبل وجود دارد"
        )




    unit = Unit(
        name=name,

    )

    db.add(unit)
    db.commit()
    db.refresh(unit)

    return {
        "success": True,
        "message": "واحد با موفقیت ایجاد شد",
        "data": {
            "branch_id": unit.id,
            "name": unit.name,

        }
    }

@router_branch.put("/{branch_id}/manager")
def set_regional_manager(
        branch_id: int,
        manager_id: int,
        db: Session = Depends(get_db)
):
    """
    تنظیم مدیر منطقه برای شعبه

    پارامترها:
    - branch_id: شناسه شعبه
    - manager_id: شناسه مدیر منطقه

    بازگشت:
    - اطلاعات به‌روز شده شعبه
    """
    # بررسی وجود شعبه
    branch = db.query(Branch).filter(
        Branch.id == branch_id
    ).first()

    if not branch:
        raise HTTPException(
            status_code=404,
            detail="شعبه یافت نشد"
        )

    # بررسی وجود مدیر
    manager = db.query(User).filter(
        User.id == manager_id
    ).first()

    if not manager:
        raise HTTPException(
            status_code=404,
            detail="مدیر یافت نشد"
        )

    # به‌روزرسانی مدیر شعبه
    branch.regional_manager_id = manager_id
    db.commit()
    db.refresh(branch)

    return {
        "success": True,
        "message": "مدیر منطقه با موفقیت تنظیم شد",
        "data": {
            "branch_id": branch.id,
            "regional_manager_id": branch.regional_manager_id,
            "branch_name": branch.name
        }
    }

@router_branch.get("/list")
def list_branches(
        db: Session = Depends(get_db)
):
    """
    دریافت لیست تمام شعبات

    پارامترهای اختیاری:
    - skip: تعداد رکوردهای رد شده (برای صفحه‌بندی)
    - limit: حداکثر تعداد رکوردهای برگشتی

    بازگشت:
    - لیست شعبات
    """
    branches = db.query(Branch).all()

    return {
        "success": True,
        "data": [
            {
                "id": branch.id,
                "name": branch.name,
                "regional_manager_name": branch.regional_manager.name if branch.regional_manager else None,

            }
            for branch in branches
        ]
    }

# --- روتر موضوعات شکایت ---
router_issues = APIRouter(prefix="/complaint-issues", tags=["Complaint Issues"])

@router_issues.post("/create")
def create_complaint_issue(
        name: str,
        db: Session = Depends(get_db)
):
    """
    ایجاد موضوع شکایت جدید

    پارامترها:
    - name: نام موضوع (الزامی)
    - description: توضیحات (اختیاری)

    بازگشت:
    - اطلاعات موضوع ایجاد شده
    """
    # بررسی وجود موضوع با همان نام
    existing = db.query(ComplaintIssue).filter(
        ComplaintIssue.name == name
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="موضوع با این نام از قبل وجود دارد"
        )

    # ایجاد موضوع جدید
    issue = ComplaintIssue(
        name=name
    )

    db.add(issue)
    db.commit()
    db.refresh(issue)

    return {
        "success": True,
        "message": "موضوع شکایت با موفقیت ایجاد شد",
        "data": {
            "id": issue.id,
            "name": issue.name,
        }
    }

@router_issues.get("/list")
def list_complaint_issues(

        db: Session = Depends(get_db)
):
    """
    دریافت لیست تمام موضوعات شکایت

    پارامترهای اختیاری:
    - skip: تعداد رکوردهای رد شده
    - limit: حداکثر تعداد رکوردهای برگشتی

    بازگشت:
    - لیست موضوعات شکایت
    """
    issues = db.query(ComplaintIssue).all()

    return {
        "success": True,
        "data": [
            {
                "id": issue.id,
                "name": issue.name,

            }
            for issue in issues
        ]
    }


@router_issues.put("/{issue_id}")
def update_complaint_issue(
        issue_id: int,
        name: str = None,
        description: str = None,
        db: Session = Depends(get_db)
):
    """
    به‌روزرسانی موضوع شکایت

    پارامترها:
    - issue_id: شناسه موضوع
    - name: نام جدید (اختیاری)
    - description: توضیحات جدید (اختیاری)

    بازگشت:
    - اطلاعات به‌روز شده موضوع
    """
    issue = db.query(ComplaintIssue).filter(
        ComplaintIssue.id == issue_id
    ).first()

    if not issue:
        raise HTTPException(
            status_code=404,
            detail="موضوع شکایت یافت نشد"
        )

    # بررسی عدم تکرار نام در صورت تغییر
    if name and name != issue.name:
        existing = db.query(ComplaintIssue).filter(
            ComplaintIssue.name == name
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="موضوع با این نام از قبل وجود دارد"
            )
        issue.name = name

    if description is not None:
        issue.description = description

    db.commit()
    db.refresh(issue)

    return {
        "success": True,
        "message": "موضوع شکایت با موفقیت به‌روزرسانی شد",
        "data": {
            "id": issue.id,
            "name": issue.name,
            "description": issue.description
        }
    }

@router_issues.delete("/{issue_id}")
def delete_complaint_issue(
        issue_id: int,
        db: Session = Depends(get_db)
):
    """
    حذف موضوع شکایت

    پارامترها:
    - issue_id: شناسه موضوع

    بازگشت:
    - تایید حذف
    """
    issue = db.query(ComplaintIssue).filter(
        ComplaintIssue.id == issue_id
    ).first()

    if not issue:
        raise HTTPException(
            status_code=404,
            detail="موضوع شکایت یافت نشد"
        )

    db.delete(issue)
    db.commit()

    return {
        "success": True,
        "message": "موضوع شکایت با موفقیت حذف شد"
    }



router_managers = APIRouter(prefix="/regional_managers", tags=["Regional Managers"])

# --- اضافه کردن مدیر منطقه جدید ---
@router_managers.post("/create")
def create_manager(name: str, db: Session = Depends(get_db)):
    # بررسی وجود مدیر با همان نام
    existing = db.query(RegionalManager).filter(RegionalManager.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Manager already exists")

    manager = RegionalManager(name=name)
    db.add(manager)
    db.commit()
    db.refresh(manager)
    return {"success": True, "manager_id": manager.id, "name": manager.name}

# --- لیست تمام مدیران منطقه ---
@router_managers.get("/list")
def list_managers(db: Session = Depends(get_db)):
    managers = db.query(RegionalManager).all()
    return [{"id": m.id, "name": m.name} for m in managers]
