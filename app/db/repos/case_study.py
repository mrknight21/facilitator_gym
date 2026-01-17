from app.db.repos.base import BaseRepo
from app.domain.schemas import CaseStudyCreate, CaseStudyOut

class CaseStudyRepo(BaseRepo):
    def __init__(self):
        super().__init__("case_studies")

    async def create(self, cs: CaseStudyCreate) -> CaseStudyOut:
        doc = cs.model_dump()
        doc["_id"] = doc["case_study_id"]
        await self.col.insert_one(doc)
        return CaseStudyOut(**doc)

    async def get(self, case_study_id: str) -> CaseStudyOut | None:
        doc = await self.col.find_one({"_id": case_study_id})
        if doc:
            return CaseStudyOut(**doc)
        return None

    async def list_all(self) -> list[CaseStudyOut]:
        cursor = self.col.find({})
        docs = await cursor.to_list(length=100)
        return [CaseStudyOut(**d) for d in docs]
