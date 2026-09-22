import 'reflect-metadata'
import express, { type Express } from 'express'
import { ExpressAdapter } from '@nestjs/platform-express'
import { NestFactory } from '@nestjs/core'
import { AppModule } from './app.module.js'

let cachedServer: Express | null = null

export async function createServer(): Promise<Express> {
  if (cachedServer) return cachedServer

  const server = express()
  const app = await NestFactory.create(AppModule, new ExpressAdapter(server), {
    logger: process.env.NODE_ENV === 'production' ? ['error', 'warn'] : ['log', 'error', 'warn'],
  })

  app.setGlobalPrefix('api')
  const corsOrigin = process.env.CORS_ORIGIN?.trim()
  if (corsOrigin) app.enableCors({ origin: corsOrigin, credentials: true })
  await app.init()

  cachedServer = server
  return server
}
