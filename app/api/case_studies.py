from fastapi import APIRouter, Depends, HTTPException
from app.domain.schemas import CaseStudyCreate, CaseStudyOut
from app.db.repos.case_study import CaseStudyRepo

router = APIRouter()

def get_repo():
    return CaseStudyRepo()

@router.post("/case-studies", response_model=CaseStudyOut)
async def create_case_study(cs: CaseStudyCreate, repo: CaseStudyRepo = Depends(get_repo)):
    existing = await repo.get(cs.case_study_id)
    if existing:
        raise HTTPException(status_code=400, detail="Case study already exists")
    return await repo.create(cs)

@router.get("/case-studies/{case_study_id}", response_model=CaseStudyOut)
async def get_case_study(case_study_id: str, repo: CaseStudyRepo = Depends(get_repo)):
    cs = await repo.get(case_study_id)
    if not cs:
        raise HTTPException(status_code=404, detail="Case study not found")
    return cs

@router.get("/case-studies", response_model=list[CaseStudyOut])
async def list_case_studies(repo: CaseStudyRepo = Depends(get_repo)):
    return await repo.list_all()
