/********************************************************************
	Rhapsody	: 9.0.2 
	Login		: Raini
	Component	: DefaultComponent 
	Configuration 	: DefaultConfig
	Model Element	: DTSRS
//!	Generated Date	: Mon, 26, Feb 2024  
	File Path	: DefaultComponent\DefaultConfig\DTSRS.cpp
*********************************************************************/

//## auto_generated
#include "DTSRS.h"
//## package BlockModeling

//## class DTSRS
//## class DTSRS::DTSRSFrame
DTSRS::DTSRSFrame::DTSRSFrame() {
}

DTSRS::DTSRSFrame::~DTSRSFrame() {
}

DTSRS::DTSRS() {
    itsDTSRSFrame = NULL;
}

DTSRS::~DTSRS() {
    cleanUpRelations();
}

DTSRS::DTSRSFrame* DTSRS::getItsDTSRSFrame() const {
    return itsDTSRSFrame;
}

void DTSRS::setItsDTSRSFrame(DTSRS::DTSRSFrame* p_DTSRSFrame) {
    itsDTSRSFrame = p_DTSRSFrame;
}

void DTSRS::cleanUpRelations() {
    if(itsDTSRSFrame != NULL)
        {
            itsDTSRSFrame = NULL;
        }
}

/*********************************************************************
	File Path	: DefaultComponent\DefaultConfig\DTSRS.cpp
*********************************************************************/
