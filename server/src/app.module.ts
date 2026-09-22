import { Module } from '@nestjs/common'
import { APP_GUARD } from '@nestjs/core'
import { MongooseModule } from '@nestjs/mongoose'
import { AdminModule } from './admin/admin.module.js'
import { EventsModule } from './events/events.module.js'
import { HeroesModule } from './heroes/heroes.module.js'
import { MetaModule } from './meta/meta.module.js'
import { RemindersModule } from './reminders/reminders.module.js'
import { UserStatusGuard } from './users/user-status.guard.js'
import { UsersModule } from './users/users.module.js'

@Module({
  imports: [
    MongooseModule.forRootAsync({
      useFactory: () => {
        const uri = process.env.MONGODB_URL?.trim()
        if (!uri) throw new Error('MONGODB_URL is required for the Vercel Mini App API')
        return {
          uri,
          dbName: process.env.MONGODB_DB_NAME?.trim() || 'erablur',
          serverSelectionTimeoutMS: 7000,
          maxPoolSize: 8,
          minPoolSize: 0,
        }
      },
    }),
    HeroesModule,
    UsersModule,
    MetaModule,
    EventsModule,
    RemindersModule,
    AdminModule,
  ],
  providers: [{ provide: APP_GUARD, useClass: UserStatusGuard }],
})
export class AppModule {}
