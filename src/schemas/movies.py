import re

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
from datetime import date, timedelta

from database.models import MovieStatusEnum


class MovieBase(BaseModel):
    name: str
    date: date
    score: float = Field(ge=0, le=100)
    overview: str
    status: MovieStatusEnum
    budget: float = Field(ge=0)
    revenue: float = Field(ge=0)

    model_config = {"from_attributes": True}


class MovieListItemSchema(BaseModel):
    id: int
    name: str
    date: date
    score: float = Field(ge=0, le=100)
    overview: str

    model_config = {"from_attributes": True}


class MovieListResponseSchema(BaseModel):
    movies: List[MovieListItemSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int


class GenreSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class ActorSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class LanguageSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class CountrySchema(BaseModel):
    id: int
    name: Optional[str]
    code: str

    model_config = {"from_attributes": True}


class MovieDetailSchema(MovieBase):
    id: int
    country: CountrySchema
    languages: List[LanguageSchema]
    genres: List[GenreSchema]
    actors: List[ActorSchema]

    model_config = {"from_attributes": True}


class MovieCreateSchema(BaseModel):
    name: str = Field(max_length=255)
    date: date
    score: float = Field(ge=0, le=100)
    overview: str
    status: MovieStatusEnum
    budget: float = Field(ge=0)
    revenue: float = Field(ge=0)
    country: str
    genres: List[str]
    actors: List[str]
    languages: List[str]

    model_config = {"from_attributes": True}

    @field_validator("date")
    @classmethod
    def date_not_too_far(cls, v: date) -> date:
        if v > date.today() + timedelta(days=365):
            raise ValueError("Movie date cannot be more than 1 year in the future")
        return v

    @field_validator("country")
    @classmethod
    def country_alpha3(cls, v: str) -> str:
        if not re.fullmatch(r"[A-Z]{2,3}", v):
            raise ValueError("Country must be a 3-letter uppercase code")
        return v



class MovieUpdateSchema(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    date: Optional[date] = None
    score: Optional[float] = Field(default=None, ge=0, le=100)
    overview: Optional[str] = None
    status: Optional[MovieStatusEnum] = None
    budget: Optional[float] = Field(default=None, ge=0)
    revenue: Optional[float] = Field(default=None, ge=0)

    model_config = {"from_attributes": True}

    @field_validator("date")
    @classmethod
    def date_not_too_far(cls, v: date) -> date:
        if v > date.today() + timedelta(days=365):
            raise ValueError("Movie date cannot be more than 1 year in the future")
        return v

    @model_validator(mode="before")
    @classmethod
    def validate_country(cls, values):
        country = values.get("country")
        if country is not None:
            country = country.upper()
            if not re.fullmatch(r"[A-Z]{2,3}", country):
                raise ValueError("Country code must be 2 or 3 uppercase letters")
            values["country"] = country
        return values



