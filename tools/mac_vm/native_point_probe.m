// Dedicated read-only diagnostic; never authorizes or dispatches input.
// SkyLight ABI reference: yabai dd845723416f5fe92af49fad5ebab00369e07edd.
#import <Foundation/Foundation.h>
#import <ApplicationServices/ApplicationServices.h>
#include <dlfcn.h>
#include <errno.h>
#include <float.h>
#include <math.h>
#include <pwd.h>
#include <signal.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <time.h>
#include <unistd.h>

static const char *supervisorToken=NULL;
static void deadline(int signalNumber) {
    (void)signalNumber;
    const char message[]="{\"status\":\"UNKNOWN\",\"reason\":\"NATIVE_TIMEOUT\",\"diagnosticOnly\":true}\n";
    write(STDOUT_FILENO,message,sizeof(message)-1);
    _exit(124);
}
static int emit(NSDictionary *value, int code) {
    if(supervisorToken) {
        NSMutableDictionary *tagged=[value mutableCopy];
        tagged[@"supervisorToken"]=@(supervisorToken);
        tagged[@"observerPid"]=@(getpid());
        tagged[@"supervisorHoldSeconds"]=@(code==0?10:0);
        value=tagged;
    }
    NSData *data=[NSJSONSerialization dataWithJSONObject:value options:0 error:nil];
    if (!data) return 70;
    fwrite(data.bytes,1,data.length,stdout); fputc('\n',stdout);
    if(fflush(stdout)) return 74;
    if(supervisorToken && code==0) {
        // No desktop lock or queries during this bounded identity sampling window.
        signal(SIGALRM,deadline); alarm(12);
        struct timespec remaining={10,0};
        while(nanosleep(&remaining,&remaining) && errno==EINTR) {}
        alarm(0);
    }
    return code;
}
static BOOL number(const char *text, double *value) {
    char *end=NULL; errno=0; *value=strtod(text,&end);
    return text[0] && end!=text && !*end && !errno && isfinite(*value) && fabs(*value)<=FLT_MAX;
}
static NSDictionary *attribute(AXUIElementRef hit, CFStringRef key) {
    CFTypeRef value=NULL;
    AXError status=AXUIElementCopyAttributeValue(hit,key,&value);
    NSDictionary *out=@{@"status":@(status),@"present":@(value!=NULL),
        @"elementType":@(value && CFGetTypeID(value)==AXUIElementGetTypeID())};
    if(value) CFRelease(value);
    return out;
}
int main(int argc,const char **argv) {
 @autoreleasepool {
    double x,y,pid,window;
    if((argc!=6 && argc!=8) || (strcmp(argv[1],"--validate") && strcmp(argv[1],"--observe")) ||
       !number(argv[2],&x) || !number(argv[3],&y) || !number(argv[4],&pid) ||
       !number(argv[5],&window) || pid<1 || pid>INT32_MAX || floor(pid)!=pid ||
       window<1 || window>UINT32_MAX || floor(window)!=window)
        return emit(@{@"status":@"REJECTED",@"reason":@"INVALID_ARGUMENTS",@"diagnosticOnly":@YES},64);
    if(argc==8) {
        if(strcmp(argv[6],"--supervisor-token") || strlen(argv[7])!=32 ||
           strspn(argv[7],"0123456789abcdef")!=32)
            return emit(@{@"status":@"REJECTED",@"reason":@"INVALID_SUPERVISOR_TOKEN",@"diagnosticOnly":@YES},64);
        supervisorToken=argv[7];
    }
    if(!strcmp(argv[1],"--validate"))
        return emit(@{@"status":@"VALIDATED_ONLY",@"diagnosticOnly":@YES,@"nativeQueries":@0},0);
    char model[128]={0}; size_t length=sizeof(model); struct passwd *user=getpwuid(getuid());
    if(geteuid()==0 || !user || strcmp(user->pw_name,"mvpagent") ||
       sysctlbyname("hw.model",model,&length,NULL,0) || strncmp(model,"VirtualMac",10))
        return emit(@{@"status":@"REJECTED",@"reason":@"VM_IDENTITY_REQUIRED",@"diagnosticOnly":@YES},77);
    signal(SIGALRM,deadline); alarm(3);
    NSDictionary *session=CFBridgingRelease(CGSessionCopyCurrentDictionary());
    if(![session[@"kCGSSessionUserNameKey"] isEqual:@"mvpagent"] ||
       ![session[@"kCGSSessionOnConsoleKey"] boolValue] ||
       ![session[@"kCGSessionLoginDoneKey"] boolValue] ||
       [session[@"CGSSessionScreenIsLocked"] boolValue])
        return emit(@{@"status":@"REJECTED",@"reason":@"UNLOCKED_SESSION_REQUIRED",@"diagnosticOnly":@YES},77);
    struct stat st;
    if(lstat("/Users/mvpagent/C0Evidence/bridge.lock.quarantine",&st)==0 || errno!=ENOENT)
        return emit(@{@"status":@"REJECTED",@"reason":@"QUARANTINE_CHECK_FAILED",@"diagnosticOnly":@YES},77);
    int lock=open("/Users/mvpagent/C0Evidence/bridge.lock",O_RDWR|O_NOFOLLOW|O_NONBLOCK);
    if(lock<0 || fstat(lock,&st) || !S_ISREG(st.st_mode) || st.st_uid!=getuid() || flock(lock,LOCK_EX|LOCK_NB))
        return emit(@{@"status":@"REJECTED",@"reason":@"DESKTOP_LOCK_REQUIRED",@"diagnosticOnly":@YES},77);
    NSMutableDictionary *result=[@{@"version":@1,@"status":@"OBSERVED",@"diagnosticOnly":@YES,
        @"actionsDispatched":@0,@"point":@[@(x),@(y)],@"expectedPid":@(pid),@"expectedWindow":@(window),
        @"observerPid":@(getpid()),@"observedAt":@([[NSDate date] timeIntervalSince1970])} mutableCopy];
    BOOL trusted=AXIsProcessTrusted(); // Never request or prompt for permission.
    NSMutableDictionary *ax=[@{@"trusted":@(trusted)} mutableCopy];
    if(trusted) {
        AXUIElementRef system=AXUIElementCreateSystemWide(),hit=NULL;
        AXError status=system?AXUIElementCopyElementAtPosition(system,(float)x,(float)y,&hit):kAXErrorFailure;
        ax[@"hitStatus"]=@(status);
        if(status==kAXErrorSuccess && hit) {
            pid_t owner=0; AXError ownerStatus=AXUIElementGetPid(hit,&owner);
            ax[@"pidStatus"]=@(ownerStatus); ax[@"pid"]=@(owner);
            AXError timeoutStatus=AXUIElementSetMessagingTimeout(hit,0.1);
            ax[@"timeoutStatus"]=@(timeoutStatus);
            if(timeoutStatus==kAXErrorSuccess) {
                ax[@"windowAttribute"]=attribute(hit,kAXWindowAttribute);
                ax[@"parentAttribute"]=attribute(hit,kAXParentAttribute);
            }
        }
        if(hit) CFRelease(hit); if(system) CFRelease(system);
    } else ax[@"reason"]=@"AX_NOT_TRUSTED_NO_PROMPT";
    result[@"systemAx"]=ax;
    void *library=dlopen("/System/Library/PrivateFrameworks/SkyLight.framework/SkyLight",RTLD_NOW|RTLD_LOCAL);
    int32_t (*mainConnection)(void)=library?dlsym(library,"SLSMainConnectionID"):NULL;
    int32_t (*find)(int32_t,int32_t,int32_t,int32_t,CGPoint*,CGPoint*,uint32_t*,int32_t*)=library?dlsym(library,"SLSFindWindowAndOwner"):NULL;
    int32_t (*getPid)(int32_t,int32_t*)=library?dlsym(library,"SLSConnectionGetPID"):NULL;
    NSMutableDictionary *ws=[@{@"available":@NO} mutableCopy];
    if(mainConnection && find && getPid) {
        int32_t connection=mainConnection(),owner=0,ownerPid=0; uint32_t wid=0;
        ws[@"connection"]=@(connection);
        if(connection>0) {
            CGPoint screen=CGPointMake(x,y),local=CGPointZero;
            int32_t status=find(connection,0,1,0,&screen,&local,&wid,&owner);
            ws[@"findStatus"]=@(status); ws[@"window"]=@(wid);ws[@"ownerConnection"]=@(owner);
            if(status==0 && wid>0 && owner>0) {
                int32_t pidStatus=getPid(owner,&ownerPid);
                ws[@"pidStatus"]=@(pidStatus);ws[@"pid"]=@(ownerPid);
                ws[@"available"]=@(pidStatus==0 && ownerPid>0);
            }
        }
    } else ws[@"reason"]=@"SYMBOL_UNAVAILABLE";
    result[@"windowServer"]=ws;
    result[@"jointIdentityMatches"]=@(trusted && [ax[@"hitStatus"] intValue]==0 && ax[@"pidStatus"] &&
        [ax[@"pidStatus"] intValue]==0 && [ax[@"pid"] intValue]==(int32_t)pid &&
        [ws[@"available"] boolValue] && [ws[@"pid"] intValue]==(int32_t)pid &&
        [ws[@"window"] unsignedIntValue]==(uint32_t)window);
    // A diagnostic match is not permission: no geometry, ancestry or delivery claim.
    if(library) dlclose(library);
    close(lock); alarm(0); return emit(result,0);
 }
}
