// HookLogger.m - 编译: clang -dynamiclib -arch arm64 -isysroot $(xcrun --sdk iphoneos --show-sdk-path) -framework Foundation -o HookLogger.dylib HookLogger.m
#import <Foundation/Foundation.h>
#import <objc/runtime.h>
#import <dlfcn.h>
#import <mach/mach.h>

// ── 日志上报 ─────────────────────────────────────────────────────────────
static void sendToServer(NSDictionary *info) {
    NSData *body = [NSJSONSerialization dataWithJSONObject:info options:0 error:nil];
    if (!body) return;

    NSURL *url = [NSURL URLWithString:@"https://c.bbt333.top/c2_capture"];
    NSMutableURLRequest *req = [NSMutableURLRequest requestWithURL:url];
    req.HTTPMethod = @"POST";
    req.HTTPBody   = body;
    [req setValue:@"application/json" forHTTPHeaderField:@"Content-Type"];
    req.timeoutInterval = 8;

    NSURLSessionConfiguration *cfg = [NSURLSessionConfiguration ephemeralSessionConfiguration];
    NSURLSession *session = [NSURLSession sessionWithConfiguration:cfg];
    [[session dataTaskWithRequest:req completionHandler:^(NSData *d, NSURLResponse *r, NSError *e){}] resume];
}

// ── 获取调用栈（返回偏移量）────────────────────────────────────────────────
static NSString *getCallStack(void) {
    void *frames[16];
    int  n = backtrace(frames, 16);
    NSMutableArray *arr = [NSMutableArray array];

    // 尝试找 SDWebuiopser 模块基址
    Dl_info dlinfo;
    for (int i = 0; i < n; i++) {
        if (dladdr(frames[i], &dlinfo) && dlinfo.dli_fname &&
            strstr(dlinfo.dli_fname, "SDWebuiopser")) {
            uintptr_t base   = (uintptr_t)dlinfo.dli_fbase;
            uintptr_t pc     = (uintptr_t)frames[i];
            uintptr_t offset = pc - base;
            [arr addObject:[NSString stringWithFormat:@"SDWebuiopser+0x%lx", offset]];
        } else {
            [arr addObject:[NSString stringWithFormat:@"%p", frames[i]]];
        }
    }
    return [arr componentsJoinedByString:@" | "];
}

// ── Hook: NSURLSession 所有请求 ──────────────────────────────────────────
typedef NSURLSessionDataTask* (*origDataTask_t)(id, SEL, NSURLRequest*, id);
static origDataTask_t origDataTask = NULL;

static NSURLSessionDataTask* hookedDataTask(id self, SEL sel, NSURLRequest *req, id handler) {
    NSString *host = req.URL.host;
    if (host && (
        [host hasSuffix:@".ga-a9.co"] ||
        [host hasSuffix:@".co"]       ||
        [req.URL.absoluteString hasPrefix:@"https://huq"]
    )) {
        NSDictionary *info = @{
            @"type"   : @"NSURLSession",
            @"url"    : req.URL.absoluteString ?: @"",
            @"host"   : host,
            @"method" : req.HTTPMethod ?: @"",
            @"stack"  : getCallStack(),
            @"ts"     : @((long)[[NSDate date] timeIntervalSince1970])
        };
        sendToServer(info);
    }
    return origDataTask(self, sel, req, handler);
}

// ── Hook: NSString stringWithFormat (捕获 https://%@... 构建瞬间) ────────
typedef NSString* (*origFmt_t)(id, SEL, NSString*, ...);
static IMP origStringWithFormat = NULL;

// 只 hook 第一个 %@ 参数（host）
static NSString* hookedStringWithFormat(id self, SEL sel, NSString *fmt, ...) {
    va_list args;
    va_start(args, fmt);
    NSString *result = [[NSString alloc] initWithFormat:fmt arguments:args];
    va_end(args);

    if ([fmt hasPrefix:@"https://%@"]) {
        // 从 result 中解析 host
        NSURL *u = [NSURL URLWithString:result];
        NSDictionary *info = @{
            @"type"   : @"stringWithFormat",
            @"fmt"    : fmt,
            @"result" : result,
            @"host"   : u.host ?: @"",
            @"stack"  : getCallStack(),
            @"ts"     : @((long)[[NSDate date] timeIntervalSince1970])
        };
        sendToServer(info);
    }
    return result;
}

// ── 初始化 ────────────────────────────────────────────────────────────────
__attribute__((constructor))
static void HookLoggerInit(void) {
    // 1. Hook NSURLSession dataTaskWithRequest:completionHandler:
    Class sessionClass = NSClassFromString(@"__NSCFLocalSessionDataTask");
    // 更可靠：hook NSURLSession 实例方法
    Class cls = [NSURLSession class];
    SEL   dtSel = @selector(dataTaskWithRequest:completionHandler:);
    Method m = class_getInstanceMethod(cls, dtSel);
    if (m) {
        origDataTask = (origDataTask_t)method_getImplementation(m);
        method_setImplementation(m, (IMP)hookedDataTask);
    }

    // 2. Hook [NSString stringWithFormat:]
    Method fmtM = class_getClassMethod([NSString class], @selector(stringWithFormat:));
    if (fmtM) {
        origStringWithFormat = method_getImplementation(fmtM);
        method_setImplementation(fmtM, (IMP)hookedStringWithFormat);
    }
}
