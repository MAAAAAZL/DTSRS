/*********************************************************************
	Rhapsody	: 9.0.2 
	Login		: Raini
	Component	: DefaultComponent 
	Configuration 	: DefaultConfig
	Model Element	: DTSRS
//!	Generated Date	: Mon, 26, Feb 2024  
	File Path	: DefaultComponent\DefaultConfig\DTSRS.h
*********************************************************************/

#ifndef DTSRS_H
#define DTSRS_H

//## auto_generated
#include <oxf\oxf.h>
//## auto_generated
#include <..\Profiles\SysML\SIDefinitions.h>
//## package BlockModeling

//## class DTSRS
class DTSRS {
public :

    //## class DTSRS::DTSRSFrame
    class DTSRSFrame {
        ////    Constructors and destructors    ////
        
    public :
    
        //## auto_generated
        DTSRSFrame();
        
        //## auto_generated
        ~DTSRSFrame();
    };
    
    ////    Constructors and destructors    ////
    
    //## auto_generated
    DTSRS();
    
    //## auto_generated
    ~DTSRS();
    
    ////    Additional operations    ////
    
    //## auto_generated
    DTSRSFrame* getItsDTSRSFrame() const;
    
    //## auto_generated
    void setItsDTSRSFrame(DTSRSFrame* p_DTSRSFrame);

protected :

    //## auto_generated
    void cleanUpRelations();
    
    ////    Relations and components    ////
    
    DTSRSFrame* itsDTSRSFrame;		//## link itsDTSRSFrame
};

#endif
/*********************************************************************
	File Path	: DefaultComponent\DefaultConfig\DTSRS.h
*********************************************************************/
