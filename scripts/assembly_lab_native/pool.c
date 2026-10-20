/* Owner experiment only. One serialized caller; matrix lifetime covers pool.
 * Sleeping persistent workers: no idle spinning, affinity or power changes. */
#include <pthread.h>
#include <stdint.h>
#include <stdlib.h>
#include <stddef.h>
#include <string.h>
#include <sys/mman.h>

extern int larpus_score_half(const void*,const float*,float*,size_t,size_t);
extern int larpus_score_float(const void*,const float*,float*,size_t,size_t);
typedef struct Pool Pool;
typedef struct {Pool *pool; int id;} Worker;
struct Pool {
 pthread_mutex_t mutex;
 pthread_cond_t work,done;
 pthread_t threads[20];Worker args[20];
 const unsigned char *matrix;const float *query;float *output;
 size_t rows,dims,width,epoch;
 int workers,created,ready,remaining,stop,status,mode;
 void *owned;size_t owned_size;
};
static void *worker(void *arg) {
 Worker *w=arg;Pool *p=w->pool;size_t seen=0;
 pthread_mutex_lock(&p->mutex);p->ready++;pthread_cond_broadcast(&p->done);
 for (;;) {
  while(!p->stop && p->epoch==seen)pthread_cond_wait(&p->work,&p->mutex);
  if(p->stop)break;
  seen=p->epoch;
  size_t first=p->rows*(size_t)w->id/(size_t)p->workers;
  size_t last=p->rows*(size_t)(w->id+1)/(size_t)p->workers;
  const void *a=p->matrix+first*p->dims*p->width;
  const float *q=p->query;float *out=p->output+first;
  pthread_mutex_unlock(&p->mutex);
  int result=p->mode==1?larpus_score_float(a,q,out,last-first,p->dims):larpus_score_half(a,q,out,last-first,p->dims);
  pthread_mutex_lock(&p->mutex);
  p->status|=result;p->remaining--;
  if(!p->remaining)pthread_cond_signal(&p->done);
 }
 pthread_mutex_unlock(&p->mutex);return NULL;
}
void lab_destroy(void *handle) {
 Pool *p=handle;if(!p)return;
 pthread_mutex_lock(&p->mutex);p->stop=1;pthread_cond_broadcast(&p->work);pthread_mutex_unlock(&p->mutex);
 for(int i=0;i<p->created;i++)pthread_join(p->threads[i],NULL);
 pthread_cond_destroy(&p->done);pthread_cond_destroy(&p->work);pthread_mutex_destroy(&p->mutex);
 if(p->owned)munmap(p->owned,p->owned_size);
 free(p);
}
const void *lab_matrix(void *handle){Pool *p=handle;return p?p->matrix:NULL;}
void *lab_create(const void *matrix,size_t rows,size_t dims,int workers,int mode) {
 if((!matrix && rows)||!dims||workers<1||workers>20||mode<0||mode>2)return NULL;
 size_t width=mode==1?4:2;
 if(dims>SIZE_MAX/width || rows>SIZE_MAX/dims/width || rows>SIZE_MAX/20)return NULL;
 Pool *p=calloc(1,sizeof(*p));if(!p)return NULL;
 p->matrix=matrix;p->rows=rows;p->dims=dims;p->width=width;p->workers=workers;p->mode=mode;
 if(pthread_mutex_init(&p->mutex,NULL)){free(p);return NULL;}
 if(pthread_cond_init(&p->work,NULL)){pthread_mutex_destroy(&p->mutex);free(p);return NULL;}
 if(pthread_cond_init(&p->done,NULL)){pthread_cond_destroy(&p->work);pthread_mutex_destroy(&p->mutex);free(p);return NULL;}
 if(mode==2 && rows){
  const size_t huge=2*1024*1024,bytes=rows*dims*width;
  if(bytes>SIZE_MAX-2*huge){lab_destroy(p);return NULL;}
  size_t rounded=(bytes+huge-1)&~(huge-1),total=rounded+huge;
  void *raw=mmap(NULL,total,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
  if(raw==MAP_FAILED){lab_destroy(p);return NULL;}
  uintptr_t aligned=((uintptr_t)raw+huge-1)&~(huge-1);
  size_t prefix=aligned-(uintptr_t)raw,suffix=total-prefix-rounded;
  if(prefix)munmap(raw,prefix);
  if(suffix)munmap((void*)(aligned+rounded),suffix);
  p->owned=(void*)aligned;p->owned_size=rounded;
  if(madvise(p->owned,rounded,MADV_HUGEPAGE)){lab_destroy(p);return NULL;}
  memcpy(p->owned,matrix,bytes);p->matrix=p->owned;
 }
 for(int i=0;i<workers;i++){
  p->args[i]=(Worker){p,i};
  if(pthread_create(&p->threads[i],NULL,worker,&p->args[i])){lab_destroy(p);return NULL;}
  p->created++;
 }
 pthread_mutex_lock(&p->mutex);
 while(p->ready<workers)pthread_cond_wait(&p->done,&p->mutex);
 pthread_mutex_unlock(&p->mutex);return p;
}
int lab_score(void *handle,const float *query,float *output) {
 Pool *p=handle;if(!p||!query||(!output && p->rows))return -1;
 if(!p->rows)return 0;
 pthread_mutex_lock(&p->mutex);
 p->query=query;p->output=output;p->remaining=p->workers;p->status=0;p->epoch++;
 pthread_cond_broadcast(&p->work);
 while(p->remaining)pthread_cond_wait(&p->done,&p->mutex);
 int status=p->status;pthread_mutex_unlock(&p->mutex);return status;
}
