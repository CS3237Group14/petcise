# invoke SourceDir generated makefile for main.pem3
main.pem3: .libraries,main.pem3
.libraries,main.pem3: package/cfg/main_pem3.xdl
	$(MAKE) -f C:\Users\nmngu\workspace_v10\cs3237_CC2650_template/src/makefile.libs

clean::
	$(MAKE) -f C:\Users\nmngu\workspace_v10\cs3237_CC2650_template/src/makefile.libs clean

