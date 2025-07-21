from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import shutil
import os

from DB.database import get_db

import pandas as pd
from sqlalchemy.orm import Session
from models.lunch import LunchMenu
import jdatetime
from datetime import date


def jalali_to_gregorian(jalali_str: str) -> date:
    # ورودی مثل: "1403/04/24"
    year, month, day = map(int, jalali_str.split("/"))
    jd = jdatetime.date(year, month, day)
    return jd.togregorian()


def load_lunch_menu_from_excel(file_path: str, db: Session):
    df = pd.read_excel(file_path)

    for _, row in df.iterrows():
        weekday = row['weekday']
        jalali_date = row['date']
        main_dish = row['main_dish']

        gregorian_date = jalali_to_gregorian(str(jalali_date))

        existing_menu = db.query(LunchMenu).filter(LunchMenu.date == gregorian_date).first()

        if existing_menu:
            # آپدیت منوی موجود
            existing_menu.main_dish = main_dish
            existing_menu.weekday = weekday
        else:
            # ایجاد منوی جدید
            new_menu = LunchMenu(
                date=gregorian_date,
                weekday=weekday,
                main_dish=main_dish
            )
            db.add(new_menu)

    db.commit()


router_excel = APIRouter()


@router_excel.post("/upload-lunch-menu/")
async def upload_lunch_menu(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="لطفاً فقط فایل اکسل بارگذاری کنید.")

    temp_file = f"/tmp/{file.filename}"
    with open(temp_file, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        load_lunch_menu_from_excel(temp_file, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در بارگذاری فایل: {str(e)}")
    finally:
        os.remove(temp_file)  # حذف فایل موقتی

    return {"message": "برنامه غذایی با موفقیت ذخیره شد."}
