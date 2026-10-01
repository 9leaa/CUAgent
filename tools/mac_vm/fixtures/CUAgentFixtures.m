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
    NSString *title=[@{@"form":@"CUAgent Form",@"scroll":@"CUAgent Scroll",@"document":@"CUAgent Document",
        @"cross_app":@"CUAgent Transfer",@"popup":@"CUAgent Popup",@"window_change":@"CUAgent Source",
        @"input_correction":@"CUAgent Correction",@"long_workflow":@"CUAgent Workflow",@"reobserve_failure":@"CUAgent Recovery"} objectForKey:self.task];
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
    }else{
        [self buildC1];
    }
    [self.window makeKeyAndOrderFront:nil];[NSApp activateIgnoringOtherApps:YES];
}
- (void)effect:(NSString *)name {
    [self.effects addObject:name];
    [self record:@{@"effects":self.effects,@"stage":@(self.stage)} name:@"c1-effects.json"];
}
- (void)field:(NSString *)name initial:(NSString *)value {
    [self label:name frame:NSMakeRect(20,365,100,25) in:self.window.contentView];
    self.code=[[NSTextField alloc] initWithFrame:NSMakeRect(120,360,460,32)];
    self.code.stringValue=value;[self.code setAccessibilityLabel:name];[self.window.contentView addSubview:self.code];
}
- (void)buildC1 {
    if([self.task isEqual:@"popup"]){
        [self button:@"Open Confirmation" frame:NSMakeRect(310,300,250,36) action:@selector(openConfirmation:)];
    }else if([self.task isEqual:@"window_change"]){
        [self button:@"Open Destination" frame:NSMakeRect(310,300,250,36) action:@selector(openDestination:)];
    }else if([self.task isEqual:@"long_workflow"]){
        self.stage=1;[self workflowPage];[self effect:@"stage:1"];
    }else{
        NSString *name=[self.task isEqual:@"cross_app"]?@"Value":@"Code";
        NSString *value=[self.task isEqual:@"input_correction"]?@"cedra-42":@"";
        [self field:name initial:value];
        [self button:@"Submit" frame:NSMakeRect(400,210,160,36) action:@selector(submitC1:)];
        if([self.task isEqual:@"input_correction"])[self effect:@"initial-value:cedra-42"];
    }
}
- (void)submitC1:(id)sender {
    NSString *prefix=[self.task isEqual:@"cross_app"]?@"Transferred":([self.task isEqual:@"reobserve_failure"]?@"Recovered":@"Submitted");
    self.status.stringValue=[NSString stringWithFormat:@"%@ %@",prefix,self.code.stringValue];
    [self record:@{@"value":self.code.stringValue,@"submitted":@YES,@"task":self.task} name:@"c1-submission.json"];
    if([self.task isEqual:@"input_correction"])[self effect:[@"corrected-value:" stringByAppendingString:self.code.stringValue]];
    [self effect:[self.task isEqual:@"cross_app"]?@"transfer-submit":([self.task isEqual:@"window_change"]?@"destination-submit":@"submit")];
}
- (void)openConfirmation:(id)sender {
    if(self.confirmation)return;
    self.confirmation=[[NSPanel alloc] initWithContentRect:NSMakeRect(420,320,420,180) styleMask:NSWindowStyleMaskTitled backing:NSBackingStoreBuffered defer:NO];
    self.confirmation.title=@"CUAgent Confirmation";self.confirmation.releasedWhenClosed=NO;
    self.confirmation.hidesOnDeactivate=NO;
    [self label:@"Confirm cedar-42?" frame:NSMakeRect(20,100,360,35) in:self.confirmation.contentView];
    NSButton *button=[NSButton buttonWithTitle:@"Confirm" target:self action:@selector(confirmPopup:)];button.frame=NSMakeRect(230,35,160,36);
    [self.confirmation.contentView addSubview:button];[self.confirmation makeKeyAndOrderFront:nil];[self effect:@"popup-opened"];
}
- (void)confirmPopup:(id)sender {
    self.status.stringValue=@"Confirmed cedar-42";
    [self effect:@"owned-popup-confirmed"];[self.confirmation close];
    [self.window makeKeyAndOrderFront:nil];
}
- (void)openDestination:(id)sender {
    self.originWindow=self.window;
    self.window=[[NSWindow alloc] initWithContentRect:NSMakeRect(380,260,640,480) styleMask:NSWindowStyleMaskTitled|NSWindowStyleMaskClosable backing:NSBackingStoreBuffered defer:NO];
    self.window.title=@"CUAgent Destination";self.window.releasedWhenClosed=NO;
    self.status=[self label:@"Not completed" frame:NSMakeRect(20,20,600,30) in:self.window.contentView];
    [self field:@"Code" initial:@""];[self button:@"Submit" frame:NSMakeRect(400,210,160,36) action:@selector(submitC1:)];
    [self.originWindow orderOut:nil];[self.window makeKeyAndOrderFront:nil];[self effect:@"destination-opened"];
}
- (void)workflowPage {
    for(NSView *view in [self.window.contentView.subviews copy])[view removeFromSuperview];
    self.status=[self label:[NSString stringWithFormat:@"Stage %ld",(long)self.stage] frame:NSMakeRect(20,20,600,30) in:self.window.contentView];
    if(self.stage==1){[self field:@"Code" initial:@""];[self button:@"Next" frame:NSMakeRect(400,210,160,36) action:@selector(nextPage:)];}
    else if(self.stage==2){[self field:@"Marker" initial:@""];[self button:@"Review" frame:NSMakeRect(400,210,160,36) action:@selector(nextPage:)];}
    else{[self label:[NSString stringWithFormat:@"Code: %@ | Marker: %@",self.note.stringValue,self.target.stringValue] frame:NSMakeRect(20,330,580,40) in:self.window.contentView];[self button:@"Confirm Submission" frame:NSMakeRect(340,210,240,36) action:@selector(finishWorkflow:)];}
}
- (void)nextPage:(id)sender {
    if(self.stage==1){self.note=[NSTextField new];self.note.stringValue=self.code.stringValue;}
    else if(self.stage==2){self.target=[NSTextField new];self.target.stringValue=self.code.stringValue;}
    else return;
    self.stage++;[self workflowPage];[self effect:[NSString stringWithFormat:@"stage:%ld",(long)self.stage]];
}
- (void)finishWorkflow:(id)sender {
    if(self.stage!=3)return;
    self.status.stringValue=[NSString stringWithFormat:@"Submitted %@ | %@ | confirmed",self.note.stringValue,self.target.stringValue];
    [self record:@{@"code":self.note.stringValue,@"marker":self.target.stringValue,@"confirmed":@YES} name:@"c1-submission.json"];
    [self effect:@"workflow-submit"];
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
    if(![@[@"form",@"scroll",@"document",@"cross_app",@"popup",@"window_change",@"input_correction",@"long_workflow",@"reobserve_failure"] containsObject:task])return 64;
    NSString *root=[NSHomeDirectory() stringByAppendingPathComponent:@"C0Evidence"];
    if(![[directory stringByDeletingLastPathComponent] isEqual:root])return 77;
    NSDictionary *attributes=[[NSFileManager defaultManager] attributesOfItemAtPath:directory error:nil];
    if(![attributes[NSFileType] isEqual:NSFileTypeDirectory])return 77;
    [NSApplication sharedApplication];NSApp.activationPolicy=NSApplicationActivationPolicyRegular;
    Fixture *fixture=[Fixture new];fixture.task=task;fixture.directory=directory;NSApp.delegate=fixture;[NSApp run];
}return 0;}
