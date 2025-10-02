from sqlalchemy.orm import selectinload, joinedload
from starlette import status

from database.models import (
    CountryModel,
    GenreModel,
    ActorModel,
    LanguageModel
)
from schemas import MovieDetailSchema
from schemas.movies import MovieUpdateSchema
from database import get_db, MovieModel
from schemas.movies import (
    MovieListItemSchema,
    MovieListResponseSchema,
    MovieCreateSchema,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc

router = APIRouter(prefix="/movies", tags=["Movies"])


@router.get(
    "/",
    response_model=MovieListResponseSchema,
    status_code=status.HTTP_200_OK
)
async def get_movies_list(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=20),
):
    count_result = await db.execute(select(func.count(MovieModel.id)))
    total_items = count_result.scalar()
    total_pages = (total_items + per_page - 1) // per_page

    if total_items == 0:
        raise HTTPException(status_code=404, detail="No movies found.")

    if page > total_pages:
        raise HTTPException(status_code=404, detail="Page out of range")

    stmt = (
        select(MovieModel)
        .order_by(desc(MovieModel.id))
        .offset(per_page * (page - 1))
        .limit(per_page)
    )
    result = await db.execute(stmt)
    movies = result.scalars().all()

    movies_data = [
        MovieListItemSchema(
            id=movie.id,
            name=movie.name,
            date=movie.date,
            score=movie.score,
            overview=movie.overview,
        )
        for movie in movies
    ]

    base_url = "/theater"
    prev_page = (
        f"{base_url}/movies/?page={page - 1}&per_page={per_page}"
        if page > 1
        else None
    )
    next_page = (
        f"{base_url}/movies/?page={page + 1}&per_page={per_page}"
        if page < total_pages
        else None
    )

    return MovieListResponseSchema(
        movies=movies_data,
        prev_page=prev_page,
        next_page=next_page,
        total_pages=total_pages,
        total_items=total_items,
    )


@router.get(
    "/{movie_id}/",
    response_model=MovieDetailSchema,
    status_code=status.HTTP_200_OK
)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MovieModel)
        .options(
            joinedload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
        )
        .where(MovieModel.id == movie_id)
    )
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(
            status_code=404, detail="Movie with the given ID was not found."
        )

    return MovieDetailSchema.model_validate(movie)


@router.post(
    "/",
    response_model=MovieDetailSchema,
    status_code=status.HTTP_201_CREATED
)
async def create_movie(
        movie_in: MovieCreateSchema,
        db: AsyncSession = Depends(get_db)
):
    stmt = select(MovieModel).where(
        MovieModel.name == movie_in.name, MovieModel.date == movie_in.date
    )
    result = await db.execute(stmt)
    existing_movie = result.scalar_one_or_none()
    if existing_movie:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A movie with the name '{movie_in.name}' and "
            f"release date '{movie_in.date}' already exists.",
        )

    country_stmt = select(CountryModel).where(
        CountryModel.code == movie_in.country
    )
    result = await db.execute(country_stmt)
    country = result.scalar_one_or_none()
    if not country:
        country = CountryModel(code=movie_in.country, name=None)
        db.add(country)
        await db.flush()

    genres = []
    for genre_name in movie_in.genres:
        stmt = select(GenreModel).where(GenreModel.name == genre_name)
        result = await db.execute(stmt)
        genre = result.scalar_one_or_none()
        if not genre:
            genre = GenreModel(name=genre_name)
            db.add(genre)
            await db.flush()
        genres.append(genre)

    actors = []
    for actor_name in movie_in.actors:
        stmt = select(ActorModel).where(ActorModel.name == actor_name)
        result = await db.execute(stmt)
        actor = result.scalar_one_or_none()
        if not actor:
            actor = ActorModel(name=actor_name)
            db.add(actor)
            await db.flush()
        actors.append(actor)

    languages = []
    for language_name in movie_in.languages:
        stmt = select(LanguageModel).where(LanguageModel.name == language_name)
        result = await db.execute(stmt)
        language = result.scalar_one_or_none()
        if not language:
            language = LanguageModel(name=language_name)
            db.add(language)
            await db.flush()
        languages.append(language)

    movie = MovieModel(
        name=movie_in.name,
        date=movie_in.date,
        score=movie_in.score,
        overview=movie_in.overview,
        status=movie_in.status,
        budget=movie_in.budget,
        revenue=movie_in.revenue,
        country=country,
        genres=genres,
        actors=actors,
        languages=languages,
    )

    db.add(movie)
    await db.commit()
    await db.refresh(
        movie, attribute_names=["genres", "actors", "languages", "country"]
    )

    return MovieDetailSchema.model_validate(movie)


@router.delete("/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(stmt)
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(
            status_code=404, detail="Movie with the given ID was not found."
        )

    await db.delete(movie)
    await db.commit()
    return


@router.patch("/{movie_id}/", status_code=status.HTTP_200_OK)
async def update_movie(
    movie_id: int,
    movie_data: MovieUpdateSchema,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MovieModel).where(MovieModel.id == movie_id)
    )
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(
            status_code=404, detail="Movie with the given ID was not found."
        )

    update_data = movie_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(movie, key, value)

    db.add(movie)
    await db.commit()
    return {"detail": "Movie updated successfully."}
