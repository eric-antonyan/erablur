import { Controller, Get, Header, Param, Query } from '@nestjs/common'
import { EventsService } from './events.service.js'

@Controller('events')
export class EventsController {
  constructor(private readonly service: EventsService) {}

  @Get()
  @Header('Cache-Control', 'no-store, max-age=0')
  list(@Query('from') from?: string, @Query('to') to?: string, @Query('limit') limit?: string) {
    return this.service.listPublic({ from, to, limit: Number(limit) })
  }

  @Get('upcoming')
  @Header('Cache-Control', 'no-store, max-age=0')
  upcoming(@Query('limit') limit?: string) {
    return this.service.upcoming(Number(limit) || 8)
  }

  @Get(':id')
  @Header('Cache-Control', 'no-store, max-age=0')
  get(@Param('id') id: string) {
    return this.service.getPublic(id)
  }
}
