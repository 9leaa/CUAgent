// Native, deterministic test surfaces. Never runs on the personal host Mac.
#import <Cocoa/Cocoa.h>
#import <sys/sysctl.h>

@interface FlippedView : NSView
@end
@implementation FlippedView
- (BOOL)isFlipped { return YES; }
@end

@interface Fixture : NSObject <NSApplicationDelegate>
@property NSWindow *window;
@property NSString *directory;
@property NSString *task;
@property NSTextField *code;
@property NSTextField *note;
@property NSTextField *status;
@property NSTextView *editor;
@property NSScrollView *scroll;
@property NSTextField *target;
@property NSWindow *originWindow;
@property NSPanel *confirmation;
@property NSInteger stage;
@property NSMutableArray *effects;
@end

@implementation Fixture
- (NSTextField *)label:(NSString *)text frame:(NSRect)rect in:(NSView *)view {
    NSTextField *label=[NSTextField labelWithString:text];label.frame=rect;[view addSubview:label];return label;
}
- (NSButton *)button:(NSString *)text frame:(NSRect)rect action:(SEL)action {
    NSButton *button=[NSButton buttonWithTitle:text target:self action:action];button.frame=rect;
    [self.window.contentView addSubview:button];return button;
}
- (void)record:(NSDictionary *)state name:(NSString *)name {
    NSData *data=[NSJSONSerialization dataWithJSONObject:state options:NSJSONWritingPrettyPrinted error:nil];
    [data writeToFile:[self.directory stringByAppendingPathComponent:name] options:NSDataWritingAtomic error:nil];
}
- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    self.effects=[NSMutableArray new];
    NSString *title=[@{@"form":@"CUAgent Form",@"scroll":@"CUAgent Scroll",@"document":@"CUAgent Document"} objectForKey:self.task];
    self.window=[[NSWindow alloc] initWithContentRect:NSMakeRect(360,240,640,480) styleMask:NSWindowStyleMaskTitled|NSWindowStyleMaskClosable backing:NSBackingStoreBuffered defer:NO];
    self.window.title=title;self.window.releasedWhenClosed=NO;
    NSView *view=self.window.contentView;
    self.status=[self label:@"Not completed" frame:NSMakeRect(20,20,600,30) in:view];
    if([self.task isEqual:@"form"]){
        [self label:@"Code" frame:NSMakeRect(20,365,100,25) in:view];
        self.code=[[NSTextField alloc] initWithFrame:NSMakeRect(120,360,460,32)];[self.code setAccessibilityLabel:@"Code"];[view addSubview:self.code];
        [self label:@"Note" frame:NSMakeRect(20,305,100,25) in:view];
        self.note=[[NSTextField alloc] initWithFrame:NSMakeRect(120,300,460,32)];[self.note setAccessibilityLabel:@"Note"];[view addSubview:self.note];
        [self button:@"Submit" frame:NSMakeRect(400,210,160,36) action:@selector(submit:)];
    }else if([self.task isEqual:@"scroll"]){
        self.scroll=[[NSScrollView alloc] initWithFrame:NSMakeRect(20,65,600,390)];self.scroll.hasVerticalScroller=YES;self.scroll.borderType=NSBezelBorder;
        [self.scroll setAccessibilityLabel:@"Task Scroll Area"];
        FlippedView *doc=[[FlippedView alloc] initWithFrame:NSMakeRect(0,0,580,2600)];
        [self label:@"Scroll down to locate the TARGET marker." frame:NSMakeRect(20,20,540,35) in:doc];
        for(int i=0;i<20;i++)[self label:[NSString stringWithFormat:@"Reference row %02d",i+1] frame:NSMakeRect(20,100+i*100,540,30) in:doc];
        self.target=[self label:@"TARGET: harbor-729" frame:NSMakeRect(20,2400,540,45) in:doc];
        self.scroll.documentView=doc;[view addSubview:self.scroll];
        self.scroll.contentView.postsBoundsChangedNotifications=YES;
        [[NSNotificationCenter defaultCenter] addObserver:self selector:@selector(scrolled:) name:NSViewBoundsDidChangeNotification object:self.scroll.contentView];
        [self scrolled:nil];
    }else if([self.task isEqual:@"document"]){
        NSScrollView *scroll=[[NSScrollView alloc] initWithFrame:NSMakeRect(20,100,600,350)];scroll.hasVerticalScroller=YES;scroll.borderType=NSBezelBorder;
        self.editor=[[NSTextView alloc] initWithFrame:NSMakeRect(0,0,580,340)];self.editor.richText=NO;[self.editor setAccessibilityLabel:@"Document Body"];
        scroll.documentView=self.editor;[view addSubview:scroll];
        [self button:@"Save Document" frame:NSMakeRect(400,58,190,36) action:@selector(save:)];
    }
    [self.window makeKeyAndOrderFront:nil];[NSApp activateIgnoringOtherApps:YES];
}
- (void)submit:(id)sender {
    [self record:@{@"code":self.code.stringValue,@"note":self.note.stringValue,@"submitted":@YES} name:@"submission.json"];
    self.status.stringValue=[NSString stringWithFormat:@"Submitted: %@ | %@",self.code.stringValue,self.note.stringValue];
}
- (void)scrolled:(NSNotification *)notification {
    NSRect visible=self.scroll.contentView.bounds;
    BOOL shown=NSContainsRect(visible,self.target.frame);
    [self record:@{@"originY":@(visible.origin.y),@"targetVisible":@(shown),@"target":@"harbor-729"} name:@"viewport.json"];
    self.status.stringValue=shown?@"TARGET visible":@"TARGET not visible";
}
- (void)save:(id)sender {
    NSSavePanel *panel=[NSSavePanel savePanel];panel.directoryURL=[NSURL fileURLWithPath:self.directory isDirectory:YES];panel.nameFieldStringValue=@"task-note.txt";panel.title=@"Save task document";panel.canCreateDirectories=NO;
    [panel beginSheetModalForWindow:self.window completionHandler:^(NSModalResponse result){
        if(result!=NSModalResponseOK)return;
        NSString *path=panel.URL.path;
        if(![path isEqual:[self.directory stringByAppendingPathComponent:@"task-note.txt"]]){self.status.stringValue=@"Denied: task directory only";return;}
        if([[NSFileManager defaultManager] fileExistsAtPath:path]){self.status.stringValue=@"Denied: no overwrite";return;}
        NSError *error=nil;
        BOOL ok=[self.editor.string writeToFile:path atomically:YES encoding:NSUTF8StringEncoding error:&error];
        self.status.stringValue=ok?@"Saved task-note.txt":@"Save failed";
        if(ok)[self record:@{@"saved":@YES,@"filename":@"task-note.txt",@"text":self.editor.string} name:@"document-save.json"];
    }];
}
- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender { return YES; }
@end

int main(int argc,const char **argv){@autoreleasepool{
    char model[128]={0};size_t size=sizeof(model);sysctlbyname("hw.model",model,&size,NULL,0);
    if(strncmp(model,"VirtualMac",10)!=0 || ![NSUserName() isEqual:@"mvpagent"])return 77;
    NSArray *args=NSProcessInfo.processInfo.arguments;
    if(args.count!=5 || ![args[1] isEqual:@"--task"] || ![args[3] isEqual:@"--output"])return 64;
    NSString *task=args[2],*directory=args[4];
    if(![@[@"form",@"scroll",@"document"] containsObject:task])return 64;
    NSString *root=[NSHomeDirectory() stringByAppendingPathComponent:@"C0Evidence"];
    if(![[directory stringByDeletingLastPathComponent] isEqual:root])return 77;
    NSDictionary *attributes=[[NSFileManager defaultManager] attributesOfItemAtPath:directory error:nil];
    if(![attributes[NSFileType] isEqual:NSFileTypeDirectory])return 77;
    [NSApplication sharedApplication];NSApp.activationPolicy=NSApplicationActivationPolicyRegular;
    Fixture *fixture=[Fixture new];fixture.task=task;fixture.directory=directory;NSApp.delegate=fixture;[NSApp run];
}return 0;}
