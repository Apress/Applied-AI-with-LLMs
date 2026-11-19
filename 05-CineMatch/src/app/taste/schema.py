from pydantic import BaseModel, Field


class TasteProfile(BaseModel):
    country: str = "IT"
    with_genre_ids: list[int] = Field(default_factory=list)
    without_genre_ids: list[int] = Field(default_factory=list)
    with_keyword_ids: list[int] = Field(default_factory=list)
    without_keyword_ids: list[int] = Field(default_factory=list)
    primary_release_date_gte: str | None = None
    primary_release_date_lte: str | None = None
    vote_average_gte: float = 6.0
    original_language: str | None = None
    sort_by: str = "popularity.desc"
    explain: list[str] = Field(default_factory=list)


class VotedMovieMetadata(BaseModel):
    tmdb_id: int
    vote_enum: str
    genre_ids: list[int]
    keyword_ids: list[int]
    release_year: int | None = None
    runtime: int | None = None
    original_language: str | None = None
