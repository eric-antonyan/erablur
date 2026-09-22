import { Controller, Get, Header } from '@nestjs/common'
import { HeroesService } from '../heroes/heroes.service.js'

@Controller()
export class MetaController {
  constructor(private readonly heroes: HeroesService) {}

  @Get('health')
  @Header('Cache-Control', 'no-store')
  health() {
    return { ok: true, service: 'hayoc-heros-miniapp-api', version: '3.0.0' }
  }

  @Get('meta')
  @Header('Cache-Control', 'public, s-maxage=300, stale-while-revalidate=1800')
  async meta() {
    const [count, filters, heroOfDay] = await Promise.all([
      this.heroes.count(),
      this.heroes.filters(),
      this.heroes.heroOfDay(),
    ])
    return { count, filters, heroOfDay }
  }
}
