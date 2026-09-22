import 'reflect-metadata'
import { NestFactory } from '@nestjs/core'
import { AppModule } from './src/app.module.js'

async function main() {
  const app = await NestFactory.create(AppModule)
  app.setGlobalPrefix('api')
  app.enableCors({ origin: true })
  await app.listen(3001, '0.0.0.0')
  console.log('API: http://localhost:3001/api')
}

main()
