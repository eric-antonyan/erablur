import { Controller, Get, Header, Param, Query } from '@nestjs/common'
import { HeroesService } from './heroes.service.js'

@Controller('heroes')
export class HeroesController {
  constructor(private readonly service: HeroesService) {}

  @Get()
  @Header('Cache-Control', 'public, s-maxage=120, stale-while-revalidate=600')
  list(
    @Query('q') q?: string,
    @Query('war') war?: string,
    @Query('region') region?: string,
    @Query('page') page?: string,
    @Query('limit') limit?: string,
  ) {
    return this.service.list({ q, war, region, page: Number(page), limit: Number(limit) })
  }

  @Get('random')
  @Header('Cache-Control', 'public, s-maxage=60, stale-while-revalidate=180')
  random(@Query('limit') limit?: string) {
    return this.service.random(Number(limit) || 6)
  }

  @Get('day')
  @Header('Cache-Control', 'public, s-maxage=1800, stale-while-revalidate=3600')
  day() {
    return this.service.heroOfDay()
  }

  @Get(':id')
  @Header('Cache-Control', 'public, s-maxage=900, stale-while-revalidate=3600')
  get(@Param('id') id: string) {
    return this.service.get(id)
  }
}
