from app.db.repos.base import BaseRepo
from app.domain.schemas import CaseStudyCreate, CaseStudyOut
from typing import Optional

class CaseStudyRepo(BaseRepo):
    def __init__(self):
        super().__init__("case_studies")

    async def create(self, cs: CaseStudyCreate) -> CaseStudyOut:
        doc = cs.model_dump()
        doc["_id"] = doc["case_study_id"]
        await self.col.insert_one(doc)
        return CaseStudyOut(**doc)

    async def get(self, case_study_id: str) -> Optional[CaseStudyOut]:
        doc = await self.col.find_one({"_id": case_study_id})
        if doc:
            if "case_study_id" not in doc:
                doc["case_study_id"] = doc["_id"]
            return CaseStudyOut(**doc)
        return None

    async def list_all(self) -> list[CaseStudyOut]:
        cursor = self.col.find({})
        docs = await cursor.to_list(length=100)
        results = []
        for d in docs:
            if "case_study_id" not in d:
                d["case_study_id"] = d["_id"]
            results.append(CaseStudyOut(**d))
        return results
