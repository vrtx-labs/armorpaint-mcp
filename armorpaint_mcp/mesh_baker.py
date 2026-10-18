"""Run with Blender --background --python mesh_baker.py -- mesh.obj maps.npz.

CPU UV-space bakers: signed curvature, AO, thickness, position, object normal,
and neutral tangent normal. Uses source OBJ coordinates (Y-up by default).
Self-baking only: this does not perform high-poly-to-low-poly normal transfer.
"""
import argparse
import json
import sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def read_obj(path):
    vertices, normals, uvs, faces, uvfaces, nfaces = [],[],[],[],[],[]
    with Path(path).open(encoding='utf-8-sig') as stream:
        for line in stream:
            words = line.split()
            if not words:
                continue
            if words[0] in ('v','vn','vt'):
                target = {'v':vertices,'vn':normals,'vt':uvs}[words[0]]
                target.append([float(v) for v in words[1:3 if words[0]=='vt' else 4]])
            elif words[0]=='f':
                corners = [w.split('/') for w in words[1:]]
                def index(value,length):
                    value=int(value)
                    return value-1 if value>0 else length+value
                for i in range(1,len(corners)-1):
                    tri = [corners[0],corners[i],corners[i+1]]
                    if any(len(c)<2 or not c[1] for c in tri):
                        raise ValueError('Mesh needs UV coordinates on every face')
                    faces.append([index(c[0],len(vertices)) for c in tri])
                    uvfaces.append([index(c[1],len(uvs)) for c in tri])
                    nfaces.append([index(c[2],len(normals)) if len(c)>2 and c[2] else -1 for c in tri])
    return (np.asarray(v) for v in (vertices,normals,uvs,faces,uvfaces,nfaces))


def bake(mesh,output,size=512,samples=16,radius=.15,up_axis='Y'):
    vertices,normals,uvs,faces,uvfaces,nfaces = read_obj(mesh)
    faces,uvfaces,nfaces = faces.astype(int),uvfaces.astype(int),nfaces.astype(int)
    if len(faces)==0:
        raise ValueError('No mesh faces')
    if uvs.min() < -.001 or uvs.max()>1.001:
        raise ValueError('This baker requires a single 0-1 UV tile')
    bounds_min,bounds_max = vertices.min(axis=0),vertices.max(axis=0)
    diagonal=float(np.linalg.norm(bounds_max-bounds_min))
    tree = BVHTree.FromPolygons([Vector(v) for v in vertices],faces.tolist(),all_triangles=True)
    fn = np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],vertices[faces[:,2]]-vertices[faces[:,0]])
    fn /= np.maximum(np.linalg.norm(fn,axis=1,keepdims=True),1e-12)
    vn = np.zeros_like(vertices)
    for i in range(3):
        np.add.at(vn,faces[:,i],fn)
    vn /= np.maximum(np.linalg.norm(vn,axis=1,keepdims=True),1e-12)
    lap,count,edge_length = np.zeros_like(vertices),np.zeros(len(vertices)),np.zeros(len(vertices))
    for a,b in ((0,1),(1,2),(2,0)):
        delta=vertices[faces[:,b]]-vertices[faces[:,a]]
        length=np.linalg.norm(delta,axis=1)
        for x,sign in ((a,1),(b,-1)):
            np.add.at(lap,faces[:,x],delta*sign)
            np.add.at(count,faces[:,x],1)
            np.add.at(edge_length,faces[:,x],length)
    lap /= np.maximum(count[:,None],1)
    curvature=.5+.5*np.tanh(-np.sum(lap*vn,axis=1)/np.maximum(edge_length/np.maximum(count,1),1e-8)*5)
    pos=np.zeros((size,size,3),np.float32)
    nor=np.zeros_like(pos)
    curv=np.full((size,size),.5,np.float32)
    coverage=np.zeros((size,size),bool)
    for face,uf,nf in zip(faces,uvfaces,nfaces):
        uv=uvs[uf].copy()*size-.5
        uv[:,1]=size-1-uv[:,1]
        lo=np.maximum(np.floor(uv.min(axis=0)).astype(int),0)
        hi=np.minimum(np.ceil(uv.max(axis=0)).astype(int),size-1)
        if np.any(hi<lo):
            continue
        x,y=np.meshgrid(np.arange(lo[0],hi[0]+1),np.arange(lo[1],hi[1]+1))
        a,b,c=uv
        denom=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(denom)<1e-10:
            continue
        w0=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/denom
        w1=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/denom
        w2=1-w0-w1
        inside=(w0>=-1e-5)&(w1>=-1e-5)&(w2>=-1e-5)
        x,y,w=x[inside],y[inside],np.stack([w0[inside],w1[inside],w2[inside]],axis=1)
        pos[y,x]=w@vertices[face]
        nor[y,x]=w@(normals[nf] if np.all(nf>=0) else vn[face])
        curv[y,x]=w@curvature[face]
        coverage[y,x]=True
    nor /= np.maximum(np.linalg.norm(nor,axis=-1,keepdims=True),1e-8)
    ao=np.ones((size,size),np.float32)
    thickness=np.ones((size,size),np.float32)
    epsilon=diagonal*1e-5
    distance=diagonal*radius
    directions=[]
    for i in range(samples):
        r=np.sqrt((i+.5)/samples)
        theta=i*2.399963229728653
        directions.append((r*np.cos(theta),r*np.sin(theta),np.sqrt(1-r*r)))
    rows,cols=np.where(coverage)
    for index,(y,x) in enumerate(zip(rows,cols)):
        n=Vector(nor[y,x])
        origin=Vector(pos[y,x])+n*epsilon
        tangent=n.cross(Vector((0,0,1)) if abs(n.z)<.9 else Vector((0,1,0))).normalized()
        bitangent=n.cross(tangent)
        hits=0
        for dx,dy,dz in directions:
            direction=tangent*dx+bitangent*dy+n*dz
            if tree.ray_cast(origin,direction,distance)[0] is not None:
                hits+=1
        ao[y,x]=1-hits/samples
        hit=tree.ray_cast(Vector(pos[y,x])-n*epsilon,-n,diagonal)
        thickness[y,x]=np.clip(hit[3]/diagonal if hit[3] is not None else 1,0,1)
        if index%25000==0:
            print(f'Bake {index}/{len(rows)}',flush=True)
    normalized=(pos-bounds_min)/np.maximum(bounds_max-bounds_min,1e-8)
    if up_axis=='Z':
        # Convert source Z-up vectors to the Painter-style Y-up mask convention.
        normalized=normalized[:,:,[0,2,1]].copy()
        nor=nor[:,:,[0,2,1]].copy()
        nor[:,:,2]*=-1
    maps={'position':normalized.astype(np.float32),'world_space_normal':(nor*.5+.5).astype(np.float32),
          'ambient_occlusion':ao,'curvature':curv,'thickness':thickness,
          'normal':np.broadcast_to(np.array([.5,.5,1],np.float32),pos.shape).copy(),
          'coverage':coverage.astype(np.float32)}
    # Four texels of edge padding. Only empty texels are filled, never across valid islands.
    valid=coverage.copy()
    for _ in range(4):
        new=valid.copy()
        for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
            adjacent=np.roll(valid,(dy,dx),(0,1))
            if dy==1: adjacent[0,:]=False
            if dy==-1: adjacent[-1,:]=False
            if dx==1: adjacent[:,0]=False
            if dx==-1: adjacent[:,-1]=False
            fill=~new & adjacent
            for key,array in maps.items():
                if key!='coverage':
                    array[fill]=np.roll(array,(dy,dx),(0,1))[fill]
            new|=fill
        valid=new
    output=Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(output,**maps)
    output.with_suffix('.json').write_text(json.dumps({'mesh':str(Path(mesh).resolve()),'resolution':size,
        'samples':samples,'ao_radius_fraction':radius,'up_axis':up_axis,'triangles':len(faces),
        'covered_texels':int(coverage.sum()),'normal':'neutral tangent; no high-poly transfer',
        'curvature':'signed vertex Laplacian approximation'},indent=2),encoding='utf-8')
    print('BAKE_COMPLETE',output,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mesh',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--size',type=int,default=512,choices=[64,128,256,512,1024,2048])
    parser.add_argument('--samples',type=int,default=16)
    parser.add_argument('--radius',type=float,default=.15)
    parser.add_argument('--up-axis',choices=['Y','Z'],default='Y')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    if not 1<=args.samples<=256 or not 0<args.radius<=2:
        parser.error('samples must be 1..256 and radius in (0,2]')
    bake(args.mesh,args.output,args.size,args.samples,args.radius,args.up_axis)
