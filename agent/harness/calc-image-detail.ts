/** Pure image derivation via the pinned official App's existing sharp dependency. */
import { createRequire } from 'node:module'
import { createHash } from 'node:crypto'
import { basename, dirname, resolve } from 'node:path'

export function detailRegion(value:any,width:number,height:number) {
  if (!value || typeof value!=='object' || Array.isArray(value)
      || Object.keys(value).sort().join(',')!=='height,left,top,width'
      || !Object.values(value).every(v=>Number.isSafeInteger(v))
      || value.left<0 || value.top<0 || value.width<16 || value.height<16
      || value.left+value.width>width || value.top+value.height>height
      || value.width*value.height>1024*1024) throw Error('Calc detail region denied')
  return {...value,scale:2}
}

export async function deriveDetail(png:Buffer,region:any,width:number,height:number) {
  const geometry=detailRegion(region,width,height)
  if(basename(process.execPath)!=='DeepSeek Harness')throw Error('Official App image runtime required')
  const require=createRequire(resolve(dirname(process.execPath),'../Resources/app.asar/dsh/package.json'))
  const sharp=require('sharp')
  if(sharp.versions.sharp!=='0.35.5')throw Error('Pinned official sharp version required')
  const source=sharp(png,{limitInputPixels:16*1024*1024,failOn:'warning'})
  const meta=await source.metadata()
  if(meta.format!=='png' || meta.width!==width || meta.height!==height || (meta.pages??1)!==1)throw Error('Calc detail source mismatch')
  const bytes:Buffer=await source.extract(region).resize(region.width*2,region.height*2,{kernel:'nearest'}).png().toBuffer()
  if(bytes.length>8*1024*1024)throw Error('Calc detail too large')
  return {bytes,geometry,sourceSha256:createHash('sha256').update(png).digest('hex'),sha256:createHash('sha256').update(bytes).digest('hex')}
}

export function originalPoint(geometry:any,x:number,y:number) {
  if(!geometry || !Number.isFinite(x) || !Number.isFinite(y) || x<0 || y<0
      || x>=geometry.width*2 || y>=geometry.height*2 || geometry.scale!==2)throw Error('Calc detail point denied')
  return {x:geometry.left+x/2,y:geometry.top+y/2}
}
